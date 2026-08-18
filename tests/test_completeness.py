"""Tests for row-level completeness checking (litscraper.extraction.completeness),
without hitting any network. `extract_structured` is monkeypatched with a
scripted sequence of return values to exercise the retry logic.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from litscraper.extraction import completeness as completeness_module
from litscraper.extraction.completeness import MaterialRowRoster, ensure_complete_rows


class _Row(BaseModel):
    label: str


class _FakeResult(BaseModel):
    rows: list[_Row] = Field(default_factory=list)


def _count_rows(result: _FakeResult) -> int:
    return len(result.rows)


def _fake_result(*labels: str) -> _FakeResult:
    return _FakeResult(rows=[_Row(label=label) for label in labels])


def _script(monkeypatch, responses):
    """Patch extract_structured to return `responses` in order, regardless
    of the prompt/response_model passed in."""
    calls = []

    def fake_extract_structured(prompt, response_model, client=None):
        calls.append((prompt, response_model))
        return responses[len(calls) - 1]

    monkeypatch.setattr(completeness_module, "extract_structured", fake_extract_structured)
    return calls


def test_no_retry_when_roster_matches_extraction(monkeypatch):
    first_pass = _fake_result("A", "B")
    roster = MaterialRowRoster(rows=["A", "B"])
    calls = _script(monkeypatch, [first_pass, roster])

    result = ensure_complete_rows(
        document_text="doc",
        extraction_prompt="extract",
        response_model=_FakeResult,
        row_kind_hint="hint",
        count_rows=_count_rows,
        client=None,
    )

    assert result is first_pass
    assert len(calls) == 2  # first pass + roster only, no retry


def test_retries_when_roster_finds_more_rows_than_extracted(monkeypatch):
    first_pass = _fake_result("A")  # under-extracted: missed row B
    roster = MaterialRowRoster(rows=["A", "B"])
    retry_pass = _fake_result("A", "B")  # retry recovers the missing row
    calls = _script(monkeypatch, [first_pass, roster, retry_pass])

    result = ensure_complete_rows(
        document_text="doc",
        extraction_prompt="extract",
        response_model=_FakeResult,
        row_kind_hint="hint",
        count_rows=_count_rows,
        client=None,
    )

    assert result is retry_pass
    assert len(calls) == 3
    # The retry prompt should include the original prompt plus the guidance suffix.
    retry_prompt = calls[2][0]
    assert "extract" in retry_prompt
    assert "2 distinct rows" in retry_prompt or "2" in retry_prompt


def test_keeps_best_attempt_if_retry_still_falls_short(monkeypatch):
    first_pass = _fake_result("A")
    roster = MaterialRowRoster(rows=["A", "B", "C"])
    retry_pass = _fake_result("A", "B")  # improved, but still short of 3
    calls = _script(monkeypatch, [first_pass, roster, retry_pass])

    result = ensure_complete_rows(
        document_text="doc",
        extraction_prompt="extract",
        response_model=_FakeResult,
        row_kind_hint="hint",
        count_rows=_count_rows,
        client=None,
    )

    assert result is retry_pass  # best available, even though incomplete
    assert len(calls) == 3


def test_does_not_retry_more_than_once(monkeypatch):
    first_pass = _fake_result("A")
    roster = MaterialRowRoster(rows=["A", "B", "C"])
    retry1 = _fake_result("A", "B")
    calls = _script(monkeypatch, [first_pass, roster, retry1])

    result = ensure_complete_rows(
        document_text="doc",
        extraction_prompt="extract",
        response_model=_FakeResult,
        row_kind_hint="hint",
        count_rows=_count_rows,
        client=None,
    )

    assert result is retry1
    assert len(calls) == 3  # first pass + roster + exactly 1 retry, never more


def test_retry_does_not_regress_below_first_pass(monkeypatch):
    first_pass = _fake_result("A", "B")  # already has 2 rows
    roster = MaterialRowRoster(rows=["A", "B", "C"])
    worse_retry = _fake_result("A")  # retry actually did worse
    calls = _script(monkeypatch, [first_pass, roster, worse_retry])

    result = ensure_complete_rows(
        document_text="doc",
        extraction_prompt="extract",
        response_model=_FakeResult,
        row_kind_hint="hint",
        count_rows=_count_rows,
        client=None,
    )

    assert result is first_pass  # keep the better attempt
    assert len(calls) == 3


def test_roster_failure_falls_back_to_first_pass(monkeypatch):
    first_pass = _fake_result("A")

    def fake_extract_structured(prompt, response_model, client=None):
        if response_model is MaterialRowRoster:
            raise RuntimeError("network error")
        return first_pass

    monkeypatch.setattr(completeness_module, "extract_structured", fake_extract_structured)

    result = ensure_complete_rows(
        document_text="doc",
        extraction_prompt="extract",
        response_model=_FakeResult,
        row_kind_hint="hint",
        count_rows=_count_rows,
        client=None,
    )

    assert result is first_pass
