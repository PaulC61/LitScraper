from litscraper.extraction.adsorption_schema import AdsorptionExtractionRow
from litscraper.extraction.catalyst_schema import CatalystExtractionRow
from litscraper.pipeline.csv_writer import (
    extraction_row_to_adsorption_row,
    extraction_row_to_catalyst_row,
)


def test_flat_adsorption_row_writes_one_csv_row():
    row = AdsorptionExtractionRow(measurement={"co2_adsorption_capacity_mmol_g": 2.4})
    assert extraction_row_to_adsorption_row(row)["co2_adsorption_capacity_mmol_g"] == 2.4


def test_flat_catalyst_row_writes_one_csv_row():
    row = CatalystExtractionRow(performance={"co2_conversion": 42.0})
    assert extraction_row_to_catalyst_row(row)["co2_conversion"] == 42.0
