from litscraper.extraction.adsorption_schema import AdsorptionExtractionRow, AdsorptionExtractionRows


def test_adsorption_row_defaults_are_empty_not_none():
    m = AdsorptionExtractionRow()
    assert m.material_properties.m2_metals_ratios == []
    assert m.measurement.co2_adsorption_capacity_mmol_g is None
    assert m.study_metadata.doi is None
    assert m.synthesis_method.calcination_temp_c is None


def test_adsorption_extraction_rows_defaults_to_empty_list():
    result = AdsorptionExtractionRows()
    assert result.rows == []


def test_adsorption_row_round_trips_json():
    m = AdsorptionExtractionRow(
        study_metadata={"doi": "10.1234/x"},
        material_properties={"m2_metals_ratios": ["Mg 3"], "m3_metals_ratios": ["Al 1"]},
    )
    result = AdsorptionExtractionRows(rows=[m])
    dumped = result.model_dump_json()
    restored = AdsorptionExtractionRows.model_validate_json(dumped)
    assert restored.rows[0].study_metadata.doi == "10.1234/x"
    assert restored.rows[0].material_properties.m2_metals_ratios == ["Mg 3"]


def test_adsorption_row_coerces_none_lists():
    m = AdsorptionExtractionRow.model_validate({"material_properties": {"anions": None}})
    assert m.material_properties.anions == []
