from litscraper.extraction.catalyst_schema import CatalystExtractionRow, CatalystExtractionRows


def test_material_id_is_optional():
    m = CatalystExtractionRow()
    assert m.material_id is None


def test_material_defaults_are_empty_not_none():
    m = CatalystExtractionRow(material_id="MgAl-LDH-1")
    assert m.metal_composition.m2_metals_ratios == []
    assert m.performance.co2_conversion is None
    assert m.study_metadata.doi is None


def test_catalyst_extraction_rows_defaults_to_empty_list():
    result = CatalystExtractionRows()
    assert result.rows == []


def test_catalyst_extraction_rows_round_trips_json():
    m = CatalystExtractionRow(
        material_id="MgAl-LDH-1",
        metal_composition={"m2_metals_ratios": ["Mg 3"], "m3_metals_ratios": ["Al 1"]},
    )
    result = CatalystExtractionRows(rows=[m])
    dumped = result.model_dump_json()
    restored = CatalystExtractionRows.model_validate_json(dumped)
    assert restored.rows[0].metal_composition.m2_metals_ratios == ["Mg 3"]


def test_catalyst_extraction_rows_coerces_none_list():
    result = CatalystExtractionRows.model_validate({"rows": None})
    assert result.rows == []
