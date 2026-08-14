from litscraper.pdf_parsing.tei_parser import parse_tei

SAMPLE_TEI = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt><title level="a" type="main">A Study of MgAl-LDH Materials</title></titleStmt>
      <sourceDesc>
        <biblStruct>
          <analytic>
            <author><persName><forename type="first">Jane</forename><surname>Doe</surname></persName></author>
          </analytic>
          <idno type="DOI">10.1234/example.2024</idno>
        </biblStruct>
      </sourceDesc>
      <publicationStmt><date when="2024-01-01">2024</date></publicationStmt>
    </fileDesc>
    <profileDesc>
      <abstract><p>This paper studies LDH adsorbents for CO2 capture.</p></abstract>
    </profileDesc>
  </teiHeader>
  <text>
    <body>
      <div>
        <head>Introduction</head>
        <p>LDH materials are widely studied.</p>
      </div>
      <figure type="table">
        <label>1</label>
        <head>BET surface areas</head>
        <table>
          <row><cell>Sample</cell><cell>BET (m2/g)</cell></row>
          <row><cell>MgAl-1</cell><cell>210.2</cell></row>
        </table>
      </figure>
    </body>
  </text>
</TEI>
"""


def test_parse_tei_extracts_metadata():
    doc = parse_tei(SAMPLE_TEI)
    assert doc.title == "A Study of MgAl-LDH Materials"
    assert doc.doi == "10.1234/example.2024"
    assert doc.year == 2024
    assert doc.authors == ["Jane Doe"]
    assert "CO2 capture" in doc.abstract


def test_parse_tei_extracts_sections_and_tables():
    doc = parse_tei(SAMPLE_TEI)
    assert len(doc.sections) == 1
    assert doc.sections[0].heading == "Introduction"
    assert len(doc.tables) == 1
    assert doc.tables[0].rows[1] == ["MgAl-1", "210.2"]


def test_to_llm_text_includes_tables_and_body():
    doc = parse_tei(SAMPLE_TEI)
    text = doc.to_llm_text()
    assert "Introduction" in text
    assert "BET surface areas" in text
    assert "210.2" in text
