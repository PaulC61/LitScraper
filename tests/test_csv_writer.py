from litscraper.extraction.adsorption_schema import AdsorptionMaterial
from litscraper.extraction.catalyst_schema import CatalyticPerformance, LDHCatalysisStudy
from litscraper.pipeline.csv_writer import (
    material_to_adsorption_rows,
    material_to_catalyst_rows,
)


def _catalyst_material(**kwargs) -> LDHCatalysisStudy:
    return LDHCatalysisStudy(material_id="MgAl-LDH-1", **kwargs)


def test_catalyst_material_without_measurements_yields_one_empty_row():
    m = _catalyst_material()
    rows = material_to_catalyst_rows(m)
    assert len(rows) == 1
    assert rows[0]["co2_conversion"] is None


def test_catalyst_rows_join_list_fields():
    m = _catalyst_material(metal_composition={"m2_metals_ratios": ["Mg 3", "Zn 0.5"], "m3_metals_ratios": ["Al 1"]})
    m.catalytic_performances = [CatalyticPerformance(co2_conversion=42.0)]
    rows = material_to_catalyst_rows(m)
    assert rows[0]["m2_metals_ratios"] == "Mg 3; Zn 0.5"
    assert rows[0]["co2_conversion"] == 42.0


def test_adsorption_material_without_measurements_yields_one_empty_row():
    m = AdsorptionMaterial(study_metadata={"doi": "10.1234/x"})
    rows = material_to_adsorption_rows(m)
    assert len(rows) == 1
    assert rows[0]["doi"] == "10.1234/x"
    assert rows[0]["co2_adsorption_capacity_mmol_g"] is None


def test_adsorption_material_with_multiple_measurements_yields_multiple_rows():
    m = AdsorptionMaterial(
        study_metadata={"doi": "10.1234/x"},
        adsorption_measurements=[
            {"adsorption_temperature_c": 25, "pressure_bar": 1.0, "co2_adsorption_capacity_mmol_g": 1.2},
            {"adsorption_temperature_c": 50, "pressure_bar": 1.0, "co2_adsorption_capacity_mmol_g": 0.8},
        ],
    )
    rows = material_to_adsorption_rows(m)
    assert len(rows) == 2
    assert rows[0]["adsorption_temperature_c"] == 25
    assert rows[1]["co2_adsorption_capacity_mmol_g"] == 0.8


def test_adsorption_rows_join_ratio_and_anion_lists():
    m = AdsorptionMaterial(
        material_properties={
            "m2_metals_ratios": ["Mg 3", "Zn 0.5"],
            "anions": ["CO3"],
            "impregnation": True,
            "impregnation_compound": "PEI",
        },
    )
    rows = material_to_adsorption_rows(m)
    assert rows[0]["m2_metals_ratios"] == "Mg 3; Zn 0.5"
    assert rows[0]["anions"] == "CO3"
    assert rows[0]["impregnation"] is True
    assert rows[0]["impregnation_compound"] == "PEI"
