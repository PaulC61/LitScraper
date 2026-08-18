"""Tests for per-paper duplicate consolidation without calling an LLM."""
from litscraper.extraction import batch_assessor
from litscraper.extraction.adsorption_schema import AdsorptionExtractionRow, AdsorptionExtractionRows
from litscraper.extraction.catalyst_schema import CatalystExtractionRow, CatalystExtractionRows


def test_adsorption_assessment_skips_empty_batch(monkeypatch):
    monkeypatch.setattr(batch_assessor, "get_client", lambda: (_ for _ in ()).throw(AssertionError()))

    assert batch_assessor.assess_adsorption_batch([]) == []


def test_catalyst_assessment_returns_structured_assessment(monkeypatch):
    original = [CatalystExtractionRow(material_id="variant-1"), CatalystExtractionRow(material_id="variant-2")]
    assessed = [CatalystExtractionRow(material_id="canonical")]
    calls = []

    def fake_extract(prompt, response_model, client):
        calls.append((prompt, response_model, client))
        return CatalystExtractionRows(rows=assessed)

    monkeypatch.setattr(batch_assessor, "get_client", lambda: "client")
    monkeypatch.setattr(batch_assessor, "extract_structured", fake_extract)

    assert batch_assessor.assess_catalyst_batch(original) == assessed
    assert len(calls) == 1
    assert calls[0][1] is CatalystExtractionRows
    assert "variant-1" in calls[0][0]


def test_assessment_failure_keeps_original_records(monkeypatch):
    original = [AdsorptionExtractionRow(), AdsorptionExtractionRow()]
    monkeypatch.setattr(batch_assessor, "get_client", lambda: "client")
    monkeypatch.setattr(batch_assessor, "extract_structured", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError()))

    assert batch_assessor.assess_adsorption_batch(original) == original