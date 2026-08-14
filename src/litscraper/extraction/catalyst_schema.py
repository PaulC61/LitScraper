"""Catalyst-performance extraction schema.

Ported field-for-field from the original project's
`ldh_batch_pipeline_catalyst.py` schema (as informed by the experimentors),
so the new pipeline's catalyst CSV stays compatible with that exact data
model: study year/DOI/abstract, synthesis conditions, M2+/M3+ metal ratios
and doping, and per-condition catalytic performance (reaction type,
temperature/pressure, feed composition, CO2 conversion and selectivities).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class StudyMetadata(BaseModel):
    year: Optional[int] = Field(default=None, description="Publication year")
    doi: Optional[str] = Field(default=None, description="DOI identifier")
    abstract: Optional[str] = Field(default=None, description="Abstract from beginning of paper")


class SynthesisMethod(BaseModel):
    method_name: Optional[str] = Field(default=None, description="Synthesis method (co-precipitation, hydrothermal, etc.)")
    metal_precursors: list[str] = Field(default_factory=list, description="List of metal precursors used (e.g., ['MgCl2', 'Zn(NO3)2', 'AlCl3'])")
    temperature: Optional[float] = Field(default=None, description="Synthesis temperature")
    temperature_units: Optional[str] = Field(default=None, description="Units for synthesis temperature")
    ph: Optional[float] = Field(default=None, description="pH during synthesis")
    aging_time_hr: Optional[float] = Field(default=None, description="Aging time if applicable")
    exfoliation: Optional[bool] = Field(default=None, description="Exfoliation step (True/False)")
    calcination_temp: Optional[float] = Field(default=None, description="Calcination temperature")
    calcination_temp_units: Optional[str] = Field(default=None, description="Units for calcination temperature")
    reduction_pretreatment: Optional[str] = Field(default=None, description="Reduction conditions (e.g., '5% H2/Ar at 500C for 2h')")

    @field_validator("metal_precursors", mode="before")
    @classmethod
    def _coerce_metal_precursors(cls, v):
        return [] if v is None else v


class MetalComposition(BaseModel):
    m2_metals_doping: list[str] = Field(default_factory=list, description="List of doped M2+ metals (e.g., ['Pt 0.1'])")
    m2_metals_ratios: list[str] = Field(default_factory=list, description="List of ratios of each M2+ metal (e.g., ['Mg 3', 'Zn 0.5'])")
    m3_metals_ratios: list[str] = Field(default_factory=list, description="List of ratios of each M3+ metal (e.g., ['Al 1', 'Fe 0.5'])")
    m2_m3_ratio: Optional[float] = Field(default=None, description="Overall M2+/M3+ ratio")
    anions: list[str] = Field(default_factory=list, description="List of anions (e.g., ['CO3', 'NO3'])")

    @field_validator("m2_metals_doping", "m2_metals_ratios", "m3_metals_ratios", "anions", mode="before")
    @classmethod
    def _coerce_list_fields(cls, v):
        return [] if v is None else v


class CatalyticPerformance(BaseModel):
    reaction_type: Optional[str] = Field(default=None, description="Type of catalytic reaction (e.g., 'thermal', 'photocatalytic')")
    temperature: Optional[float] = Field(default=None, description="Catalytic reaction temperature")
    temperature_units: Optional[str] = Field(default=None, description="Units for catalytic reaction temperature")
    pressure: Optional[float] = Field(default=None, description="Reaction pressure")
    pressure_units: Optional[str] = Field(default=None, description="Units for catalytic reaction pressure")
    feed_composition: Optional[str] = Field(default=None, description="Feed composition")
    co2_conversion: Optional[float] = Field(default=None, description="CO2 conversion (%)")
    co_selectivity: Optional[float] = Field(default=None, description="CO selectivity (%)")
    ch4_selectivity: Optional[float] = Field(default=None, description="CH4 (methane) selectivity (%)")
    methanol_selectivity: Optional[float] = Field(default=None, description="Methanol selectivity (%)")


class LDHCatalysisStudy(BaseModel):
    material_id: Optional[str] = Field(default=None)
    study_metadata: StudyMetadata = Field(default_factory=StudyMetadata)
    synthesis_conditions: SynthesisMethod = Field(default_factory=SynthesisMethod)
    metal_composition: MetalComposition = Field(default_factory=MetalComposition)
    catalytic_performances: list[CatalyticPerformance] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_nested_defaults(cls, data):
        if not isinstance(data, dict):
            return data
        if data.get("study_metadata") is None:
            data["study_metadata"] = {}
        if data.get("synthesis_conditions") is None:
            data["synthesis_conditions"] = {}
        if data.get("metal_composition") is None:
            data["metal_composition"] = {}
        return data

    @field_validator("catalytic_performances", mode="before")
    @classmethod
    def _coerce_performance_list(cls, v):
        return [] if v is None else v


class StudiesInPaper(BaseModel):
    """Top-level object the LLM is asked to return for a single paper's catalyst data."""

    LDH_materials: list[LDHCatalysisStudy] = Field(default_factory=list)

    @field_validator("LDH_materials", mode="before")
    @classmethod
    def _coerce_materials(cls, v):
        return [] if v is None else v
