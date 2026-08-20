"""CLI entrypoint: batch-process a folder of PDFs into two CSVs.

Usage:
    pixi run extract -- --pdf-dir LDHCatPDFs --out-dir outputs --tag most_relevant

Resumability: a `<tag>_processed.json` manifest in --out-dir records which
PDF filenames have already been processed. Re-running with the same --tag
skips papers that succeeded *and* yielded at least one material, and retries
the rest (errors, and successes that extracted nothing), appending to the
existing CSVs and manifest. Use --skip-empty to also skip zero-material
papers, or --force to reprocess everything from scratch.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from litscraper.config import settings
from litscraper.extraction.batch_assessor import assess_adsorption_batch, assess_catalyst_batch
from litscraper.extraction.extractor import extract_adsorption_from_text, extract_catalyst_from_text
from litscraper.pdf_parsing.grobid_client import GrobidUnavailableError, is_alive, pdf_to_tei
from litscraper.pdf_parsing.tei_parser import parse_tei
from litscraper.pipeline.csv_writer import (
    ADSORPTION_FIELDNAMES,
    CATALYST_FIELDNAMES,
    append_rows,
    extraction_row_to_adsorption_row,
    extraction_row_to_catalyst_row,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _load_manifest(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, indent=2, default=str))


def _needs_processing(entry: dict, retry_empty: bool) -> bool:
    """True if a previously-recorded paper should be attempted again."""
    if entry.get("status") != "ok":
        return True
    if not retry_empty:
        return False
    n_found = entry.get("n_catalyst_materials", 0) + entry.get("n_adsorption_materials", 0)
    return n_found == 0


def process_pdf(pdf_path: Path) -> tuple[list, list]:
    """Returns (catalyst_materials, adsorption_materials)."""
    tei_xml = pdf_to_tei(pdf_path)
    document = parse_tei(tei_xml)
    text = document.to_llm_text()
    catalyst_result = extract_catalyst_from_text(text)
    adsorption_result = extract_adsorption_from_text(text)
    catalyst_materials = catalyst_result.rows
    adsorption_materials = adsorption_result.rows
    if settings.do_batch_assessment:
        catalyst_materials = assess_catalyst_batch(catalyst_materials)
        adsorption_materials = assess_adsorption_batch(adsorption_materials)
    return catalyst_materials, adsorption_materials


def run(pdf_dir: Path, out_dir: Path, tag: str, force: bool = False, retry_empty: bool = True) -> None:
    if not is_alive():
        logger.error(
            "GROBID is not reachable. Start it with `pixi run grobid-up` (or `docker compose up -d`) "
            "and wait ~30s for it to warm up."
        )
        sys.exit(1)

    manifest_path = out_dir / f"{tag}_processed.json"
    manifest = {} if force else _load_manifest(manifest_path)

    adsorption_csv = out_dir / f"{tag}_adsorption.csv"
    catalyst_csv = out_dir / f"{tag}_catalyst.csv"

    pdf_paths = sorted(pdf_dir.glob("*.pdf"))
    logger.info("Found %d PDFs in %s", len(pdf_paths), pdf_dir)

    pending = [p for p in pdf_paths if p.name not in manifest or _needs_processing(manifest[p.name], retry_empty)]
    if manifest:
        logger.info(
            "Resuming tag %r: %d already complete, %d to (re)process",
            tag, len(pdf_paths) - len(pending), len(pending),
        )

    for pdf_path in pending:
        key = pdf_path.name
        attempts = manifest.get(key, {}).get("attempts", 0) + 1

        logger.info("Processing %s (attempt %d)", key, attempts)
        try:
            catalyst_materials, adsorption_materials = process_pdf(pdf_path)
        except GrobidUnavailableError as exc:
            logger.error("GROBID failed on %s: %s", key, exc)
            manifest[key] = {"status": "error", "stage": "grobid", "error": str(exc), "attempts": attempts}
            _save_manifest(manifest_path, manifest)
            continue
        except Exception as exc:  # noqa: BLE001 - keep the batch going on per-paper failures
            logger.exception("Extraction failed on %s", key)
            manifest[key] = {"status": "error", "stage": "extraction", "error": str(exc), "attempts": attempts}
            _save_manifest(manifest_path, manifest)
            continue

        append_rows(
            catalyst_csv,
            CATALYST_FIELDNAMES,
            [extraction_row_to_catalyst_row(row) for row in catalyst_materials],
        )
        append_rows(
            adsorption_csv,
            ADSORPTION_FIELDNAMES,
            [extraction_row_to_adsorption_row(row) for row in adsorption_materials],
        )

        manifest[key] = {
            "status": "ok",
            "n_catalyst_materials": len(catalyst_materials),
            "n_adsorption_materials": len(adsorption_materials),
            "attempts": attempts,
        }
        _save_manifest(manifest_path, manifest)
        logger.info(
            "Wrote %d catalyst + %d adsorption materials from %s",
            len(catalyst_materials), len(adsorption_materials), key,
        )

    logger.info("Done. Adsorption CSV: %s | Catalyst CSV: %s", adsorption_csv, catalyst_csv)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract LDH material data from PDFs into CSV.")
    parser.add_argument("--pdf-dir", type=Path, required=True, help="Folder of source PDFs.")
    parser.add_argument("--out-dir", type=Path, default=Path("outputs"), help="Folder to write CSVs/manifest to.")
    parser.add_argument("--tag", type=str, default="run", help="Prefix for output filenames.")
    parser.add_argument("--force", action="store_true", help="Reprocess PDFs even if already in the manifest.")
    parser.add_argument(
        "--skip-empty",
        action="store_true",
        help="Don't retry papers that previously succeeded but extracted zero materials.",
    )
    args = parser.parse_args()

    run(
        pdf_dir=args.pdf_dir,
        out_dir=args.out_dir,
        tag=args.tag,
        force=args.force,
        retry_empty=not args.skip_empty,
    )


if __name__ == "__main__":
    main()
