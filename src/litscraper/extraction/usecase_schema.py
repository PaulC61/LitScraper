"""LDH material use-case extraction schema.

A variant of the adsorption schema: the same study/synthesis/composition
fields, but the CO2-adsorption-specific measurement block is replaced by a
free list of use cases reported for the material. The nested sub-models are
reused from `adsorption_schema` so the shared columns stay identical across
both CSVs.

One row per distinct material (not per measurement condition).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from litscraper.extraction.adsorption_schema import (
    AdsorptionMaterialProperties,
    AdsorptionStudyMetadata,
    AdsorptionSynthesisMethod,
)


class UseCaseExtractionRow(BaseModel):
    """One LDH material and every use case the paper reports for it."""

    material_id: Optional[str] = Field(default=None, description="Material name/label as used in the paper (e.g., 'Mg3Al-CO3', 'CuMgAl-2')")
    study_metadata: AdsorptionStudyMetadata = Field(default_factory=AdsorptionStudyMetadata)
    synthesis_method: AdsorptionSynthesisMethod = Field(default_factory=AdsorptionSynthesisMethod)
    material_properties: AdsorptionMaterialProperties = Field(default_factory=AdsorptionMaterialProperties)
    use_cases: list[str] = Field(
        default_factory=list,
        description=(
            "List of applications this material is used for or evaluated for in the paper "
            "(e.g., ['adsorbent CO2', 'adsorbent heavy metals', 'catalyst CO2 hydrogenation', "
            "'paint stabilizer', 'drug delivery']). Use a short '<role> <target>' phrase per "
            "use case and leave the list empty if none is reported."
        ),
    )

    @field_validator("use_cases", mode="before")
    @classmethod
    def _coerce_use_cases(cls, v):
        if v is None:
            return []
        return [v] if isinstance(v, str) else v

    @model_validator(mode="before")
    @classmethod
    def _coerce_nested_defaults(cls, data):
        if not isinstance(data, dict):
            return data
        for field_name in ("study_metadata", "synthesis_method", "material_properties"):
            if data.get(field_name) is None:
                data[field_name] = {}
        return data


class UseCaseExtractionRows(BaseModel):
    """Flat extraction response: exactly one item per distinct material."""

    rows: list[UseCaseExtractionRow] = Field(
        default_factory=list,
        description=(
            "Every distinct LDH material in the paper, each with all of its "
            "reported use cases collected into one item. Never split one "
            "material across multiple items."
        ),
    )

    @field_validator("rows", mode="before")
    @classmethod
    def _coerce_rows(cls, value):
        return [] if value is None else value
