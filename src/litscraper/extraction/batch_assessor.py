"""Consolidate duplicate extraction variants within one paper's result batch."""
from __future__ import annotations

import logging

from litscraper.extraction.adsorption_schema import AdsorptionExtractionRows, AdsorptionExtractionRow
from litscraper.extraction.catalyst_schema import CatalystExtractionRows, CatalystExtractionRow
from litscraper.extraction.llm_client import extract_structured, get_client
from litscraper.extraction.prompts import (
    ADSORPTION_BATCH_ASSESSMENT_PROMPT,
    CATALYST_BATCH_ASSESSMENT_PROMPT,
)

logger = logging.getLogger(__name__)


def assess_catalyst_batch(rows: list[CatalystExtractionRow]) -> list[CatalystExtractionRow]:
    """Return one best-supported record for each unique catalyst-condition row."""
    if not rows:
        return rows
    result = CatalystExtractionRows(rows=rows)
    try:
        assessed = extract_structured(
            CATALYST_BATCH_ASSESSMENT_PROMPT.format(batch_json=result.model_dump_json(indent=2)),
            CatalystExtractionRows,
            client=get_client(),
        )
        return assessed.rows
    except Exception:
        logger.exception("Catalyst batch assessment failed; keeping unassessed records")
        return rows


def assess_adsorption_batch(rows: list[AdsorptionExtractionRow]) -> list[AdsorptionExtractionRow]:
    """Return one best-supported record for each unique adsorption-condition row."""
    if not rows:
        return rows
    result = AdsorptionExtractionRows(rows=rows)
    try:
        assessed = extract_structured(
            ADSORPTION_BATCH_ASSESSMENT_PROMPT.format(batch_json=result.model_dump_json(indent=2)),
            AdsorptionExtractionRows,
            client=get_client(),
        )
        return assessed.rows
    except Exception:
        logger.exception("Adsorption batch assessment failed; keeping unassessed records")
        return rows