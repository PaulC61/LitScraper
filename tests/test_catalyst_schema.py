from litscraper.extraction.catalyst_schema import LDHCatalysisStudy, StudiesInPaper


def test_material_id_is_optional():
    m = LDHCatalysisStudy()
    assert m.material_id is None


def test_material_defaults_are_empty_not_none():
    m = LDHCatalysisStudy(material_id="MgAl-LDH-1")
    assert m.metal_composition.m2_metals_ratios == []
    assert m.catalytic_performances == []
    assert m.study_metadata.doi is None


def test_studies_in_paper_defaults_to_empty_list():
    result = StudiesInPaper()
    assert result.LDH_materials == []


def test_studies_in_paper_round_trips_json():
    m = LDHCatalysisStudy(
        material_id="MgAl-LDH-1",
        metal_composition={"m2_metals_ratios": ["Mg 3"], "m3_metals_ratios": ["Al 1"]},
    )
    result = StudiesInPaper(LDH_materials=[m])
    dumped = result.model_dump_json()
    restored = StudiesInPaper.model_validate_json(dumped)
    assert restored.LDH_materials[0].metal_composition.m2_metals_ratios == ["Mg 3"]


def test_studies_in_paper_coerces_none_list():
    result = StudiesInPaper.model_validate({"LDH_materials": None})
    assert result.LDH_materials == []
