"""Orchestrates a single paper's extraction: parsed document -> validated
extraction result(s), with an optional per-material verification pass.

Because DeepSeek's context window comfortably fits a full paper (GROBID
output for a typical journal article is a few thousand to ~20k tokens), we
extract in one shot instead of the old pipeline's page-chunking + multi-
process multi-pass approach. The optional verification pass still re-checks
each material individually against the source text, which is where the old
pipeline's accuracy gains actually came from -- not from chunking.

Catalyst-focused data and adsorption-measurement data are extracted as two
independent passes with two different schemas (mirroring the original
project's separate catalyst/adsorption pipeline scripts), since they target
different tables/sections of a paper and each schema is a fixed external
contract ported from the experimentor-authored files -- see
`catalyst_schema.py` (from `ldh_batch_pipeline_catalyst.py`) and
`adsorption_schema.py` (from `patent_EVA_ldh_batch_pipeline_adsorption_simplified.py`).

Each pass also runs an optional row-level completeness check (see
`completeness.py`): a "row" is one material-measurement pair (one material
under one test condition), and a material tested under several conditions
must contribute one row per condition. The check counts rows against a
cheap roster call and retries extraction with explicit guidance if the
first pass under-counted -- this catches the common failure mode where a
multi-row results table only has its first/most prominent row extracted.
"""
from __future__ import annotations

import logging

from litscraper.config import settings
from litscraper.extraction.adsorption_schema import AdsorptionExtractionResult, AdsorptionMaterial
from litscraper.extraction.catalyst_schema import LDHCatalysisStudy, StudiesInPaper
from litscraper.extraction.completeness import ensure_complete_rows
from litscraper.extraction.llm_client import extract_structured, get_client
from litscraper.extraction.prompts import (
    ADSORPTION_EXTRACTION_PROMPT,
    ADSORPTION_VERIFICATION_PROMPT,
    CATALYST_EXTRACTION_PROMPT,
    CATALYST_VERIFICATION_PROMPT,
)

logger = logging.getLogger(__name__)


def _count_catalyst_rows(result: StudiesInPaper) -> int:
    """One row = one material tested under one reaction condition."""
    return sum(max(1, len(m.catalytic_performances)) for m in result.LDH_materials)


def _count_adsorption_rows(result: AdsorptionExtractionResult) -> int:
    """One row = one material tested under one adsorption condition."""
    return sum(max(1, len(m.adsorption_measurements)) for m in result.materials)


def extract_catalyst_from_text(document_text: str) -> StudiesInPaper:
    client = get_client()
    prompt = CATALYST_EXTRACTION_PROMPT.format(document_text=document_text)

    if settings.do_completeness_check:
        result = ensure_complete_rows(
            document_text,
            prompt,
            StudiesInPaper,
            row_kind_hint=(
                "Each row is one LDH catalyst material tested under one "
                "reaction condition (temperature, pressure, feed ratio, etc.)."
            ),
            count_rows=_count_catalyst_rows,
            client=client,
            max_retries=settings.completeness_max_retries,
        )
    else:
        result = extract_structured(prompt, StudiesInPaper, client=client)

    if settings.do_verification_pass and result.LDH_materials:
        result.LDH_materials = [
            _verify_material(
                material,
                document_text,
                verification_prompt=CATALYST_VERIFICATION_PROMPT,
                response_model=LDHCatalysisStudy,
                client=client,
            )
            for material in result.LDH_materials
        ]
    return result


def extract_adsorption_from_text(document_text: str) -> AdsorptionExtractionResult:
    client = get_client()
    prompt = ADSORPTION_EXTRACTION_PROMPT.format(document_text=document_text)

    if settings.do_completeness_check:
        result = ensure_complete_rows(
            document_text,
            prompt,
            AdsorptionExtractionResult,
            row_kind_hint=(
                "Each row is one LDH material tested under one adsorption "
                "condition (temperature, pressure, gas composition, etc.)."
            ),
            count_rows=_count_adsorption_rows,
            client=client,
            max_retries=settings.completeness_max_retries,
        )
    else:
        result = extract_structured(prompt, AdsorptionExtractionResult, client=client)

    if settings.do_verification_pass and result.materials:
        result.materials = [
            _verify_material(
                material,
                document_text,
                verification_prompt=ADSORPTION_VERIFICATION_PROMPT,
                response_model=AdsorptionMaterial,
                client=client,
            )
            for material in result.materials
        ]
    return result


def _verify_material(material, document_text: str, verification_prompt: str, response_model: type, client):
    prompt = verification_prompt.format(
        material_json=material.model_dump_json(indent=2),
        document_text=document_text,
    )
    try:
        return extract_structured(prompt, response_model, client=client)
    except Exception:
        material_label = getattr(material, "material_id", None) or "material"
        logger.exception("Verification pass failed for %s; keeping first-pass result", material_label)
        return material
