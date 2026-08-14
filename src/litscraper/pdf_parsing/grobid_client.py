"""Thin client for a locally-running GROBID service.

GROBID (github.com/kermitt2/grobid) is purpose-built for scientific PDFs: it
recovers reading order in multi-column layouts, separates body text from
references/footnotes, and preserves table structure -- all things plain
per-page text extraction (e.g. pypdf) throws away. We call the
`processFulltextDocument` endpoint, which returns a TEI XML document.
"""
from __future__ import annotations

from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from litscraper.config import settings


class GrobidUnavailableError(RuntimeError):
    """Raised when the GROBID service cannot be reached or errors out."""


def is_alive(base_url: str | None = None) -> bool:
    base_url = base_url or settings.grobid_url
    try:
        resp = requests.get(f"{base_url}/api/isalive", timeout=5)
        return resp.ok
    except requests.RequestException:
        return False


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20))
def pdf_to_tei(pdf_path: Path, base_url: str | None = None) -> str:
    """Send a PDF to GROBID and return the raw TEI XML string.

    Raises GrobidUnavailableError if the service is unreachable or returns
    a non-2xx status after retries.
    """
    base_url = base_url or settings.grobid_url
    url = f"{base_url}/api/processFulltextDocument"
    with open(pdf_path, "rb") as fh:
        files = {"input": (pdf_path.name, fh, "application/pdf")}
        data = {
            "consolidateHeader": "1",
            "consolidateCitations": "0",
            "includeRawCitations": "0",
            "teiCoordinates": "false",
        }
        try:
            resp = requests.post(url, files=files, data=data, timeout=settings.grobid_timeout_s)
        except requests.RequestException as exc:
            raise GrobidUnavailableError(f"Could not reach GROBID at {base_url}: {exc}") from exc

    if resp.status_code != 200:
        raise GrobidUnavailableError(
            f"GROBID returned status {resp.status_code} for {pdf_path.name}: {resp.text[:500]}"
        )
    return resp.text
