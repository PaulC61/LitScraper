"""Row-completeness check: makes sure an extraction pass captured every
distinct material-measurement row reported in a paper, not just a
representative subset.

A "row" here is one material-measurement pair -- one material evaluated
under one specific test condition (e.g. one line of a catalytic performance
or adsorption results table). A single material tested under several
conditions (different temperatures, pressures, feed ratios, etc.)
contributes one row per condition, not one row per material.

Approach: after the main extraction pass, a single cheap "roster" call asks
the model to enumerate every distinct material-measurement row it can find
in the paper (short labels only, no full schema) -- this establishes one
fixed expectation of how many rows there should be. It's compared against
how many rows the main pass actually produced, and if the main pass
under-counted, exactly one retry of the full extraction is made, telling the
model explicitly which rows are expected. Whichever of the two attempts
produced more rows is kept. The roster is only ever called once per paper,
and at most one retry is made -- this check does not loop.
"""
from __future__ import annotations

import logging
from typing import Callable, TypeVar

from pydantic import BaseModel, Field

from litscraper.extraction.llm_client import extract_structured

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class MaterialRowRoster(BaseModel):
    """Lightweight enumeration of every material-measurement row in a paper,
    used only to count what SHOULD have been extracted -- not the actual
    schema."""

    rows: list[str] = Field(
        default_factory=list,
        description=(
            "One short label per distinct material-measurement row (e.g. "
            "'NiAl-2 @ 350C', 'sample A, 0.5 bar CO2'). Each row = one "
            "material evaluated under one specific condition; a material "
            "tested under N conditions contributes N rows."
        ),
    )


ROSTER_PROMPT_TEMPLATE = """
Enumerate every distinct material-measurement row reported in this paper's
tables and text. Do not extract full details -- just list them.

A "row" is one material evaluated under one specific condition (e.g. one
line of a results table). If the same material was tested under several
different conditions (temperatures, pressures, feed ratios, etc.), count
each condition as a separate row. Include every row, even if several rows
share the same underlying material/synthesis.

{row_kind_hint}

Paper content:
---
{document_text}
---
""".strip()


COMPLETENESS_RETRY_SUFFIX = """

IMPORTANT -- completeness check: your previous extraction attempt only
produced {actual_rows} material-measurement row(s), but the paper appears to
report {expected_rows} distinct rows in total:
{expected_row_labels}

Re-extract the COMPLETE set of materials from scratch, making sure every one
of the {expected_rows} rows above is represented in your output -- either as
a new material entry, or as an additional entry in an existing material's
measurement/performance list if it's the same material under a different
condition. Do not drop or merge distinct rows together.
""".rstrip()


def ensure_complete_rows(
    document_text: str,
    extraction_prompt: str,
    response_model: type[T],
    row_kind_hint: str,
    count_rows: Callable[[T], int],
    client,
) -> T:
    """Run `extraction_prompt` and check row-level completeness against a
    single roster call, making at most one retry of the full extraction (with
    explicit guidance) if it under-counted. Returns whichever of the two
    attempts produced the most rows.
    """
    best_result = extract_structured(extraction_prompt, response_model, client=client)
    best_rows = count_rows(best_result)

    try:
        roster_prompt = ROSTER_PROMPT_TEMPLATE.format(
            row_kind_hint=row_kind_hint, document_text=document_text
        )
        roster = extract_structured(roster_prompt, MaterialRowRoster, client=client)
    except Exception:
        logger.exception("Row-completeness roster check failed; skipping retry")
        return best_result

    expected_rows = len(roster.rows)
    if expected_rows <= best_rows:
        return best_result

    logger.warning(
        "Completeness check: extraction produced %d row(s) but the paper appears to report %d; retrying extraction once",
        best_rows, expected_rows,
    )

    retry_prompt = extraction_prompt + COMPLETENESS_RETRY_SUFFIX.format(
        actual_rows=best_rows,
        expected_rows=expected_rows,
        expected_row_labels="\n".join(f"- {row}" for row in roster.rows),
    )
    try:
        candidate = extract_structured(retry_prompt, response_model, client=client)
        candidate_rows = count_rows(candidate)
        if candidate_rows > best_rows:
            best_result, best_rows = candidate, candidate_rows
    except Exception:
        logger.exception("Completeness retry pass failed; keeping first-pass result")

    if best_rows < expected_rows:
        logger.warning(
            "Completeness check: still only %d/%d expected row(s) after one retry; keeping best attempt",
            best_rows, expected_rows,
        )
    return best_result
