"""CLI entrypoint: batch-process a folder of PDFs into one CSV per schema.

Usage:
    pixi run extract -- --pdf-dir LDHCatPDFs --out-dir outputs --tag most_relevant
    pixi run extract -- --pdf-dir LDHCatPDFs --tag most_relevant --schemas usecase

Three independent extraction schemas are available (`catalyst`, `adsorption`,
`usecase`); all run by default. Each selected schema costs one LLM pass per
paper, so `--schemas` is the lever for trading coverage against runtime.

Resumability: a `<tag>_processed.json` manifest in --out-dir records which
PDF filenames have already been processed. Re-running with the same --tag
skips papers that succeeded *and* yielded at least one material for every
selected schema, and retries the rest (errors, and successes that extracted
nothing), appending to the existing CSVs and manifest. Use --skip-empty to
also skip zero-material papers, or --force to reprocess everything from
scratch.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from litscraper.config import settings
from litscraper.extraction.batch_assessor import (
    assess_adsorption_batch,
    assess_catalyst_batch,
    assess_usecase_batch,
)
from litscraper.extraction.extractor import (
    extract_adsorption_from_text,
    extract_catalyst_from_text,
    extract_usecases_from_text,
)
from litscraper.pdf_parsing.grobid_client import GrobidUnavailableError, is_alive, pdf_to_tei
from litscraper.pdf_parsing.tei_parser import parse_tei
from litscraper.pipeline.csv_writer import (
    ADSORPTION_FIELDNAMES,
    CATALYST_FIELDNAMES,
    USECASE_FIELDNAMES,
    append_rows,
    extraction_row_to_adsorption_row,
    extraction_row_to_catalyst_row,
    extraction_row_to_usecase_row,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SchemaSpec:
    """Everything needed to run one extraction schema end to end."""

    name: str
    extract: Callable[[str], Any]
    assess: Callable[[list], list]
    fieldnames: list[str]
    to_csv_row: Callable[[Any], dict[str, Any]]

    @property
    def manifest_key(self) -> str:
        return f"n_{self.name}_materials"


SCHEMAS: dict[str, SchemaSpec] = {
    "catalyst": SchemaSpec(
        "catalyst", extract_catalyst_from_text, assess_catalyst_batch,
        CATALYST_FIELDNAMES, extraction_row_to_catalyst_row,
    ),
    "adsorption": SchemaSpec(
        "adsorption", extract_adsorption_from_text, assess_adsorption_batch,
        ADSORPTION_FIELDNAMES, extraction_row_to_adsorption_row,
    ),
    "usecase": SchemaSpec(
        "usecase", extract_usecases_from_text, assess_usecase_batch,
        USECASE_FIELDNAMES, extraction_row_to_usecase_row,
    ),
}
DEFAULT_SCHEMAS = list(SCHEMAS)


def _load_manifest(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, indent=2, default=str))


def _needs_processing(entry: dict, retry_empty: bool, specs: list[SchemaSpec]) -> bool:
    """True if a previously-recorded paper should be attempted again."""
    if entry.get("status") != "ok":
        return True
    # A schema that never ran for this paper has no recorded count.
    if any(spec.manifest_key not in entry for spec in specs):
        return True
    if not retry_empty:
        return False
    return sum(entry.get(spec.manifest_key, 0) for spec in specs) == 0


def process_pdf(pdf_path: Path, specs: list[SchemaSpec] | None = None) -> dict[str, list]:
    """Returns {schema name: extracted rows} for each selected schema."""
    specs = specs or list(SCHEMAS.values())
    tei_xml = pdf_to_tei(pdf_path)
    document = parse_tei(tei_xml)
    text = document.to_llm_text()

    results: dict[str, list] = {}
    for spec in specs:
        rows = spec.extract(text).rows
        if settings.do_batch_assessment:
            rows = spec.assess(rows)
        results[spec.name] = rows
    return results


def run(
    pdf_dir: Path,
    out_dir: Path,
    tag: str,
    force: bool = False,
    retry_empty: bool = True,
    schemas: list[str] | None = None,
) -> None:
    if not is_alive():
        logger.error(
            "GROBID is not reachable. Start it with `pixi run grobid-up` (or `docker compose up -d`) "
            "and wait ~30s for it to warm up."
        )
        sys.exit(1)

    specs = [SCHEMAS[name] for name in (schemas or DEFAULT_SCHEMAS)]
    manifest_path = out_dir / f"{tag}_processed.json"
    manifest = {} if force else _load_manifest(manifest_path)
    csv_paths = {spec.name: out_dir / f"{tag}_{spec.name}.csv" for spec in specs}

    pdf_paths = sorted(pdf_dir.glob("*.pdf"))
    logger.info(
        "Found %d PDFs in %s; running schemas: %s",
        len(pdf_paths), pdf_dir, ", ".join(spec.name for spec in specs),
    )

    pending = [
        p for p in pdf_paths
        if p.name not in manifest or _needs_processing(manifest[p.name], retry_empty, specs)
    ]
    if manifest:
        logger.info(
            "Resuming tag %r: %d already complete, %d to (re)process",
            tag, len(pdf_paths) - len(pending), len(pending),
        )

    for pdf_path in pending:
        key = pdf_path.name
        previous = manifest.get(key, {})
        attempts = previous.get("attempts", 0) + 1

        logger.info("Processing %s (attempt %d)", key, attempts)
        try:
            results = process_pdf(pdf_path, specs)
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

        for spec in specs:
            append_rows(
                csv_paths[spec.name],
                spec.fieldnames,
                [spec.to_csv_row(row) for row in results[spec.name]],
            )

        # Counts from schemas not selected this run are carried over.
        counts = {k: v for k, v in previous.items() if k.startswith("n_")}
        counts.update({spec.manifest_key: len(results[spec.name]) for spec in specs})
        manifest[key] = {"status": "ok", **counts, "attempts": attempts}
        _save_manifest(manifest_path, manifest)
        logger.info(
            "Wrote %s from %s",
            " + ".join(f"{len(results[spec.name])} {spec.name}" for spec in specs),
            key,
        )

    logger.info("Done. %s", " | ".join(f"{name}: {path}" for name, path in csv_paths.items()))


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
    parser.add_argument(
        "--schemas",
        nargs="+",
        choices=DEFAULT_SCHEMAS,
        default=DEFAULT_SCHEMAS,
        metavar="SCHEMA",
        help=(
            "Which extraction schemas to run (one LLM pass each): "
            f"{', '.join(DEFAULT_SCHEMAS)}. Default: all."
        ),
    )
    args = parser.parse_args()

    run(
        pdf_dir=args.pdf_dir,
        out_dir=args.out_dir,
        tag=args.tag,
        force=args.force,
        retry_empty=not args.skip_empty,
        schemas=list(dict.fromkeys(args.schemas)),
    )


if __name__ == "__main__":
    main()
