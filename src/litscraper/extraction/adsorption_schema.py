"""Adsorption-measurement extraction schema.

Ported field-for-field from the original project's
`patent_EVA_ldh_batch_pipeline_adsorption_simplified.py` schema, so the new
pipeline's adsorption CSV stays compatible with that exact data model
(study title/DOI, synthesis conditions, composition ratios/doping,
impregnation, and per-condition adsorption measurements including gas
composition and wet/dry air).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class AdsorptionStudyMetadata(BaseModel):
    doi: Optional[str] = Field(default=None, description="DOI identifier")
    title: Optional[str] = Field(default=None, description="Paper title")


class AdsorptionSynthesisMethod(BaseModel):
    method_name: list[str] = Field(default_factory=list, description="Ordered list of synthesis method steps (e.g., ['co-precipitation', 'exfoliation']) if the synthesis involved multiple steps")
    metal_precursors: list[str] = Field(default_factory=list, description="List of metal precursors used (e.g., ['MgCl2', 'Zn(NO3)2', 'AlCl3'])")
    temperature: Optional[float] = Field(default=None, description="Synthesis temperature")
    temperature_units: Optional[str] = Field(default=None, description="Units for synthesis temperature")
    ph: Optional[float] = Field(default=None, description="pH during synthesis")
    aging_time_hr: Optional[float] = Field(default=None, description="Aging time if applicable")
    exfoliation: Optional[bool] = Field(default=None, description="Exfoliation step (True/False)")
    calcination_temp_c: Optional[float] = Field(default=None, description="Calcination temperature in Celsius")

    @field_validator("method_name", mode="before")
    @classmethod
    def _coerce_method_name(cls, v):
        if v is None:
            return []
        return [v] if isinstance(v, str) else v

    @field_validator("metal_precursors", mode="before")
    @classmethod
    def _coerce_metal_precursors(cls, v):
        return [] if v is None else v


class AdsorptionMaterialProperties(BaseModel):
    m2_metals_doping: list[str] = Field(default_factory=list, description="List of doped M2+ metals (e.g., ['Pt 0.1'])")
    m2_metals_ratios: list[str] = Field(default_factory=list, description="List of ratios of each M2+ metal (e.g., ['Mg 3', 'Zn 0.5'])")
    m3_metals_ratios: list[str] = Field(default_factory=list, description="List of ratios of each M3+ metal (e.g., ['Al 1', 'Fe 0.5'])")
    m2_m3_ratio: Optional[float] = Field(default=None, description="Overall M2+/M3+ ratio")
    anions: list[str] = Field(default_factory=list, description="List of anions (e.g., ['CO3', 'NO3'])")
    impregnation: Optional[bool] = Field(default=None, description="True if the material was impregnated with a polymer or compound, False otherwise")
    impregnation_compound: Optional[str] = Field(default=None, description="Name of the compound or polymer used for impregnation, if applicable")

    @field_validator("m2_metals_doping", "m2_metals_ratios", "m3_metals_ratios", "anions", mode="before")
    @classmethod
    def _coerce_list(cls, v):
        return [] if v is None else v


class AdsorptionMeasurement(BaseModel):
    adsorption_temperature_c: Optional[float] = Field(default=None, description="Adsorption temperature in C")
    pressure_bar: Optional[float] = Field(default=None, description="Pressure in bar during adsorption test")
    gas_composition: Optional[str] = Field(default=None, description="Gas composition used in adsorption test")
    wet_dry_air: Optional[bool] = Field(default=None, description="True if air is wet or contains humidity, False if dry air, None if not specified")
    co2_adsorption_capacity_mmol_g: Optional[float] = Field(default=None, description="CO2 adsorption capacity in mmol/g")


class AdsorptionExtractionRow(BaseModel):
    """One complete material-condition-measurement triplet."""

    study_metadata: AdsorptionStudyMetadata = Field(default_factory=AdsorptionStudyMetadata)
    synthesis_method: AdsorptionSynthesisMethod = Field(default_factory=AdsorptionSynthesisMethod)
    material_properties: AdsorptionMaterialProperties = Field(default_factory=AdsorptionMaterialProperties)
    measurement: AdsorptionMeasurement = Field(default_factory=AdsorptionMeasurement)

    @model_validator(mode="before")
    @classmethod
    def _coerce_nested_defaults(cls, data):
        if not isinstance(data, dict):
            return data
        for field_name in ("study_metadata", "synthesis_method", "material_properties", "measurement"):
            if data.get(field_name) is None:
                data[field_name] = {}
        return data


class AdsorptionExtractionRows(BaseModel):
    """Flat extraction response: exactly one item per reported result row."""

    rows: list[AdsorptionExtractionRow] = Field(
        default_factory=list,
        description=(
            "Every distinct material-condition-measurement triplet in the paper. "
            "Repeat material metadata in separate items when one material has "
            "multiple adsorption conditions. Never put multiple measurements in "
            "one item."
        ),
    )

    @field_validator("rows", mode="before")
    @classmethod
    def _coerce_rows(cls, value):
        return [] if value is None else value



