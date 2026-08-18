"""Consolidate duplicate extraction variants within one paper's result batch."""
from __future__ import annotations

import logging

from litscraper.extraction.adsorption_schema import AdsorptionExtractionResult, AdsorptionMaterial
from litscraper.extraction.catalyst_schema import LDHCatalysisStudy, StudiesInPaper
from litscraper.extraction.llm_client import extract_structured, get_client
from litscraper.extraction.prompts import (
    ADSORPTION_BATCH_ASSESSMENT_PROMPT,
    CATALYST_BATCH_ASSESSMENT_PROMPT,
)

logger = logging.getLogger(__name__)


def assess_catalyst_batch(materials: list[LDHCatalysisStudy]) -> list[LDHCatalysisStudy]:
    """Return one best-supported record for each unique catalyst-condition row."""
    if not materials:
        return materials
    result = StudiesInPaper(LDH_materials=materials)
    try:
        assessed = extract_structured(
            CATALYST_BATCH_ASSESSMENT_PROMPT.format(batch_json=result.model_dump_json(indent=2)),
            StudiesInPaper,
            client=get_client(),
        )
        return assessed.LDH_materials
    except Exception:
        logger.exception("Catalyst batch assessment failed; keeping unassessed records")
        return materials


def assess_adsorption_batch(materials: list[AdsorptionMaterial]) -> list[AdsorptionMaterial]:
    """Return one best-supported record for each unique adsorption-condition row."""
    if not materials:
        return materials
    result = AdsorptionExtractionResult(materials=materials)
    try:
        assessed = extract_structured(
            ADSORPTION_BATCH_ASSESSMENT_PROMPT.format(batch_json=result.model_dump_json(indent=2)),
            AdsorptionExtractionResult,
            client=get_client(),
        )
        return assessed.materials
    except Exception:
        logger.exception("Adsorption batch assessment failed; keeping unassessed records")
        return materials