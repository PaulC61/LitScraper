"""Flatten extracted records into CSV rows.

Two CSVs are produced, mirroring the two output tables the old project
maintained (adsorption-focused and catalyst-performance-focused), from two
independent extraction passes:
    * one row per flat AdsorptionExtractionRow.
    * one row per flat CatalystExtractionRow.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from litscraper.extraction.adsorption_schema import AdsorptionExtractionRow
from litscraper.extraction.catalyst_schema import CatalystExtractionRow

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


def extraction_row_to_adsorption_row(row: AdsorptionExtractionRow) -> dict[str, Any]:
    """Flatten one flat adsorption extraction item into exactly one CSV row."""
    meta = row.study_metadata
    synth = row.synthesis_method
    props = row.material_properties
    measurement = row.measurement
    return {
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
        "adsorption_temperature_c": measurement.adsorption_temperature_c,
        "pressure_bar": measurement.pressure_bar,
        "gas_composition": measurement.gas_composition,
        "wet_dry_air": measurement.wet_dry_air,
        "co2_adsorption_capacity_mmol_g": measurement.co2_adsorption_capacity_mmol_g,
    }


def extraction_row_to_catalyst_row(row: CatalystExtractionRow) -> dict[str, Any]:
    """Flatten one flat catalyst extraction item into exactly one CSV row."""
    meta = row.study_metadata
    synth = row.synthesis_conditions
    comp = row.metal_composition
    performance = row.performance
    return {
        "material_id": row.material_id,
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
        "m2_metals_doping": _join(comp.m2_metals_doping),
        "m2_metals_ratios": _join(comp.m2_metals_ratios),
        "m3_metals_ratios": _join(comp.m3_metals_ratios),
        "m2_m3_ratio": comp.m2_m3_ratio,
        "anions": _join(comp.anions),
        "reaction_type": performance.reaction_type,
        "temperature": performance.temperature,
        "temperature_units": performance.temperature_units,
        "pressure": performance.pressure,
        "pressure_units": performance.pressure_units,
        "feed_composition": performance.feed_composition,
        "co2_conversion": performance.co2_conversion,
        "co_selectivity": performance.co_selectivity,
        "ch4_selectivity": performance.ch4_selectivity,
        "methanol_selectivity": performance.methanol_selectivity,
    }


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
