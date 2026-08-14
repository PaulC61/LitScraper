"""Parse GROBID's TEI XML output into a structured, LLM-friendly document.

Unlike raw per-page PDF text, TEI gives us explicit section boundaries and
table markup, so we can:
  * drop bibliography/reference-list noise before it reaches the LLM
  * keep tables intact (a common location for synthesis/property data that
    gets scrambled by naive text extraction)
  * cite the section a claim came from, which is useful for debugging
"""
from __future__ import annotations

from dataclasses import dataclass, field

from lxml import etree

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


@dataclass
class Section:
    heading: str
    text: str


@dataclass
class Table:
    label: str
    caption: str
    rows: list[list[str]] = field(default_factory=list)

    def as_text(self) -> str:
        lines = [f"Table {self.label}: {self.caption}".strip(": ")]
        for row in self.rows:
            lines.append(" | ".join(cell.strip() for cell in row))
        return "\n".join(lines)


@dataclass
class ParsedDocument:
    title: str | None
    doi: str | None
    authors: list[str]
    year: int | None
    abstract: str
    sections: list[Section]
    tables: list[Table]

    def to_llm_text(self, max_chars: int | None = None) -> str:
        """Render the document as a single text blob for LLM extraction.

        Tables are appended after the body text (clearly labeled) rather
        than interleaved, since GROBID does not reliably anchor a table to
        its exact in-body citation point.
        """
        parts: list[str] = []
        header = f"Title: {self.title or 'UNKNOWN'}\nDOI: {self.doi or 'UNKNOWN'}\nYear: {self.year or 'UNKNOWN'}"
        parts.append(header)
        if self.abstract:
            parts.append(f"Abstract:\n{self.abstract}")
        for sec in self.sections:
            parts.append(f"## {sec.heading}\n{sec.text}")
        if self.tables:
            parts.append("## Tables")
            for table in self.tables:
                parts.append(table.as_text())
        text = "\n\n".join(parts)
        if max_chars is not None and len(text) > max_chars:
            text = text[:max_chars]
        return text


def _text_or_empty(el: etree._Element | None) -> str:
    if el is None:
        return ""
    return " ".join(el.itertext()).strip()


def _find_doi(root: etree._Element) -> str | None:
    idno = root.find(".//tei:teiHeader//tei:idno[@type='DOI']", TEI_NS)
    if idno is not None and idno.text:
        return idno.text.strip()
    return None


def _find_year(root: etree._Element) -> int | None:
    date_el = root.find(".//tei:teiHeader//tei:publicationStmt/tei:date", TEI_NS)
    if date_el is not None:
        when = date_el.get("when")
        if when and when[:4].isdigit():
            return int(when[:4])
    return None


def _find_authors(root: etree._Element) -> list[str]:
    authors = []
    for pers in root.findall(".//tei:teiHeader//tei:sourceDesc//tei:author/tei:persName", TEI_NS):
        surname = pers.find("tei:surname", TEI_NS)
        forename = pers.find("tei:forename", TEI_NS)
        name = " ".join(x.text for x in (forename, surname) if x is not None and x.text)
        if name:
            authors.append(name.strip())
    return authors


def _find_sections(root: etree._Element) -> list[Section]:
    sections: list[Section] = []
    body = root.find(".//tei:text/tei:body", TEI_NS)
    if body is None:
        return sections
    for div in body.findall(".//tei:div", TEI_NS):
        head_el = div.find("tei:head", TEI_NS)
        heading = _text_or_empty(head_el) or "Untitled section"
        # Exclude the heading itself and nested figure/table text from the running body text.
        paragraphs = [
            _text_or_empty(p)
            for p in div.findall("tei:p", TEI_NS)
        ]
        text = "\n".join(p for p in paragraphs if p)
        if text:
            sections.append(Section(heading=heading, text=text))
    return sections


def _find_tables(root: etree._Element) -> list[Table]:
    tables: list[Table] = []
    for fig in root.findall(".//tei:text//tei:figure[@type='table']", TEI_NS):
        label_el = fig.find("tei:label", TEI_NS)
        head_el = fig.find("tei:head", TEI_NS)
        label = _text_or_empty(label_el)
        caption = _text_or_empty(head_el)
        rows: list[list[str]] = []
        for row in fig.findall(".//tei:table/tei:row", TEI_NS):
            cells = [_text_or_empty(cell) for cell in row.findall("tei:cell", TEI_NS)]
            if cells:
                rows.append(cells)
        if rows or caption:
            tables.append(Table(label=label, caption=caption, rows=rows))
    return tables


def parse_tei(tei_xml: str) -> ParsedDocument:
    root = etree.fromstring(tei_xml.encode("utf-8"))

    title_el = root.find(".//tei:teiHeader//tei:titleStmt/tei:title", TEI_NS)
    title = _text_or_empty(title_el) or None

    abstract_el = root.find(".//tei:teiHeader//tei:abstract", TEI_NS)
    abstract = _text_or_empty(abstract_el)

    return ParsedDocument(
        title=title,
        doi=_find_doi(root),
        authors=_find_authors(root),
        year=_find_year(root),
        abstract=abstract,
        sections=_find_sections(root),
        tables=_find_tables(root),
    )
