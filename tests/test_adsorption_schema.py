from litscraper.extraction.adsorption_schema import AdsorptionExtractionResult, AdsorptionMaterial


def test_adsorption_material_defaults_are_empty_not_none():
    m = AdsorptionMaterial()
    assert m.material_properties.m2_metals_ratios == []
    assert m.adsorption_measurements == []
    assert m.study_metadata.doi is None
    assert m.synthesis_method.calcination_temp_c is None


def test_adsorption_extraction_result_defaults_to_empty_list():
    result = AdsorptionExtractionResult()
    assert result.materials == []


def test_adsorption_material_round_trips_json():
    m = AdsorptionMaterial(
        study_metadata={"doi": "10.1234/x"},
        material_properties={"m2_metals_ratios": ["Mg 3"], "m3_metals_ratios": ["Al 1"]},
    )
    result = AdsorptionExtractionResult(materials=[m])
    dumped = result.model_dump_json()
    restored = AdsorptionExtractionResult.model_validate_json(dumped)
    assert restored.materials[0].study_metadata.doi == "10.1234/x"
    assert restored.materials[0].material_properties.m2_metals_ratios == ["Mg 3"]


def test_adsorption_material_coerces_none_lists():
    m = AdsorptionMaterial.model_validate({"material_properties": {"anions": None}})
    assert m.material_properties.anions == []
