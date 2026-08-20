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

Each extraction item is one material-condition-measurement triplet. This
flat output shape makes every results-table row explicit, instead of asking
the model to construct nested material-to-measurement lists.
"""
from __future__ import annotations

import logging

from litscraper.config import settings
from litscraper.extraction.adsorption_schema import AdsorptionExtractionRow, AdsorptionExtractionRows
from litscraper.extraction.catalyst_schema import CatalystExtractionRow, CatalystExtractionRows
from litscraper.extraction.llm_client import extract_structured, get_client
from litscraper.extraction.prompts import (
    ADSORPTION_FLAT_EXTRACTION_PROMPT,
    ADSORPTION_FLAT_VERIFICATION_PROMPT,
    CATALYST_FLAT_EXTRACTION_PROMPT,
    CATALYST_FLAT_VERIFICATION_PROMPT,
    USECASE_FLAT_EXTRACTION_PROMPT,
    USECASE_FLAT_VERIFICATION_PROMPT,
)
from litscraper.extraction.usecase_schema import UseCaseExtractionRow, UseCaseExtractionRows

logger = logging.getLogger(__name__)


def extract_catalyst_from_text(document_text: str) -> CatalystExtractionRows:
    client = get_client()
    prompt = CATALYST_FLAT_EXTRACTION_PROMPT.format(document_text=document_text)

    result = extract_structured(prompt, CatalystExtractionRows, client=client)

    if settings.do_verification_pass and result.rows:
        result.rows = [
            _verify_material(
                row,
                document_text,
                verification_prompt=CATALYST_FLAT_VERIFICATION_PROMPT,
                response_model=CatalystExtractionRow,
                client=client,
            )
            for row in result.rows
        ]
    return result


def extract_adsorption_from_text(document_text: str) -> AdsorptionExtractionRows:
    client = get_client()
    prompt = ADSORPTION_FLAT_EXTRACTION_PROMPT.format(document_text=document_text)

    result = extract_structured(prompt, AdsorptionExtractionRows, client=client)

    if settings.do_verification_pass and result.rows:
        result.rows = [
            _verify_material(
                row,
                document_text,
                verification_prompt=ADSORPTION_FLAT_VERIFICATION_PROMPT,
                response_model=AdsorptionExtractionRow,
                client=client,
            )
            for row in result.rows
        ]
    return result


def extract_usecases_from_text(document_text: str) -> UseCaseExtractionRows:
    client = get_client()
    prompt = USECASE_FLAT_EXTRACTION_PROMPT.format(document_text=document_text)

    result = extract_structured(prompt, UseCaseExtractionRows, client=client)

    if settings.do_verification_pass and result.rows:
        result.rows = [
            _verify_material(
                row,
                document_text,
                verification_prompt=USECASE_FLAT_VERIFICATION_PROMPT,
                response_model=UseCaseExtractionRow,
                client=client,
            )
            for row in result.rows
        ]
    return result


def _verify_material(material, document_text: str, verification_prompt: str, response_model: type, client):
    prompt = verification_prompt.format(
        row_json=material.model_dump_json(indent=2),
        document_text=document_text,
    )
    try:
        return extract_structured(prompt, response_model, client=client)
    except Exception:
        material_label = getattr(material, "material_id", None) or "material"
        logger.exception("Verification pass failed for %s; keeping first-pass result", material_label)
        return material
