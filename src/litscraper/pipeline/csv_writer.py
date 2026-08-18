"""Flatten extracted records into CSV rows.

Two CSVs are produced, mirroring the two output tables the old project
maintained (adsorption-focused and catalyst-performance-focused), from two
independent extraction passes:
  * one row per (AdsorptionMaterial, AdsorptionMeasurement) pair -- schema
    ported from `patent_EVA_ldh_batch_pipeline_adsorption_simplified.py`.
  * one row per (Material, CatalyticPerformance) pair.
A material reported without any measurements of a given kind still gets one
row (with those columns empty) so it isn't silently dropped.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from litscraper.extraction.adsorption_schema import AdsorptionMaterial
from litscraper.extraction.catalyst_schema import LDHCatalysisStudy

ADSORPTION_FIELDNAMES = [
    "doi", "title", "synthesis_method", "metal_precursors",
    "synthesis_temperature", "synthesis_temperature_units", "ph", "aging_time_hr",
    "exfoliation", "calcination_temp_c",
    "m2_metals_doping", "m2_metals_ratios", "m3_metals_ratios", "m2_m3_ratio", "anions",
    "impregnation", "impregnation_compound",
    "adsorption_temperature_c", "pressure_bar", "gas_composition", "wet_dry_air",
    "co2_adsorption_capacity_mmol_g",
]

CATALYST_FIELDNAMES = [
    "material_id", "year", "doi", "title",
    "synthesis_method", "metal_precursors", "synthesis_temperature", "synthesis_temperature_units",
    "ph", "aging_time_hr", "exfoliation", "calcination_temp", "calcination_temp_units",
    "reduction_pretreatment",
    "m2_metals_doping", "m2_metals_ratios", "m3_metals_ratios", "m2_m3_ratio", "anions",
    "reaction_type", "temperature", "temperature_units", "pressure", "pressure_units",
    "feed_composition", "co2_conversion", "co_selectivity", "ch4_selectivity", "methanol_selectivity",
]


def _join(values) -> str:
    return "; ".join(str(v) for v in values if v is not None and str(v).strip() != "")


def material_to_adsorption_rows(material: AdsorptionMaterial) -> list[dict[str, Any]]:
    meta = material.study_metadata
    synth = material.synthesis_method
    props = material.material_properties

    base = {
        "doi": meta.doi,
        "title": meta.title,
        "synthesis_method": _join(synth.method_name),
        "metal_precursors": _join(synth.metal_precursors),
        "synthesis_temperature": synth.temperature,
        "synthesis_temperature_units": synth.temperature_units,
        "ph": synth.ph,
        "aging_time_hr": synth.aging_time_hr,
        "exfoliation": synth.exfoliation,
        "calcination_temp_c": synth.calcination_temp_c,
        "m2_metals_doping": _join(props.m2_metals_doping),
        "m2_metals_ratios": _join(props.m2_metals_ratios),
        "m3_metals_ratios": _join(props.m3_metals_ratios),
        "m2_m3_ratio": props.m2_m3_ratio,
        "anions": _join(props.anions),
        "impregnation": props.impregnation,
        "impregnation_compound": props.impregnation_compound,
    }

    if not material.adsorption_measurements:
        return [{**base, "adsorption_temperature_c": None, "pressure_bar": None, "gas_composition": None, "wet_dry_air": None, "co2_adsorption_capacity_mmol_g": None}]

    rows = []
    for meas in material.adsorption_measurements:
        rows.append({
            **base,
            "adsorption_temperature_c": meas.adsorption_temperature_c,
            "pressure_bar": meas.pressure_bar,
            "gas_composition": meas.gas_composition,
            "wet_dry_air": meas.wet_dry_air,
            "co2_adsorption_capacity_mmol_g": meas.co2_adsorption_capacity_mmol_g,
        })
    return rows


def _base_row(material: LDHCatalysisStudy) -> dict[str, Any]:
    meta = material.study_metadata
    synth = material.synthesis_conditions
    return {
        "material_id": material.material_id,
        "year": meta.year,
        "doi": meta.doi,
        "title": meta.title,
        "synthesis_method": _join(synth.method_name),
        "metal_precursors": _join(synth.metal_precursors),
        "synthesis_temperature": synth.temperature,
        "synthesis_temperature_units": synth.temperature_units,
        "ph": synth.ph,
        "aging_time_hr": synth.aging_time_hr,
        "exfoliation": synth.exfoliation,
        "calcination_temp": synth.calcination_temp,
        "calcination_temp_units": synth.calcination_temp_units,
        "reduction_pretreatment": synth.reduction_pretreatment,
    }


def material_to_catalyst_rows(material: LDHCatalysisStudy) -> list[dict[str, Any]]:
    base = _base_row(material)
    comp = material.metal_composition
    base.update(
        m2_metals_doping=_join(comp.m2_metals_doping),
        m2_metals_ratios=_join(comp.m2_metals_ratios),
        m3_metals_ratios=_join(comp.m3_metals_ratios),
        m2_m3_ratio=comp.m2_m3_ratio,
        anions=_join(comp.anions),
    )
    if not material.catalytic_performances:
        return [{
            **base, "reaction_type": None, "temperature": None, "temperature_units": None,
            "pressure": None, "pressure_units": None, "feed_composition": None,
            "co2_conversion": None, "co_selectivity": None, "ch4_selectivity": None,
            "methanol_selectivity": None,
        }]
    rows = []
    for perf in material.catalytic_performances:
        rows.append({
            **base,
            "reaction_type": perf.reaction_type,
            "temperature": perf.temperature,
            "temperature_units": perf.temperature_units,
            "pressure": perf.pressure,
            "pressure_units": perf.pressure_units,
            "feed_composition": perf.feed_composition,
            "co2_conversion": perf.co2_conversion,
            "co_selectivity": perf.co_selectivity,
            "ch4_selectivity": perf.ch4_selectivity,
            "methanol_selectivity": perf.methanol_selectivity,
        })
    return rows


def append_rows(csv_path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    file_exists = csv_path.exists()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)
