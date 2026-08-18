# aerleumLitScraperV2

A ground-up rewrite of `aerleumLitScraper`: extracts LDH (Layered Double
Hydroxide) material synthesis, composition, and CO2 adsorption/catalytic
performance data from scientific PDFs into CSV, with a leaner and more
reliable pipeline.

## What changed vs. the old pipeline, and why

| Stage | Old | New | Why |
|---|---|---|---|
| PDF → text | `pypdf` per-page `extract_text()` | [GROBID](https://github.com/kermitt2/grobid) → structured TEI XML (sections, tables, header metadata) | Scientific PDFs are multi-column with figures/tables; naive per-page extraction scrambles reading order and mangles tables, which is exactly where synthesis/property data lives. GROBID is purpose-built for scholarly documents. |
| Structured extraction | `scrapegraphai.SmartScraperGraph` (web-scraping graph engine repurposed for local text) + DeepSeek | Direct DeepSeek API call (still DeepSeek, via its OpenAI-compatible endpoint) through [`instructor`](https://github.com/instructor-ai/instructor) (schema-validated structured outputs with automatic retry) | scrapegraphai's abstraction (fetch/render/parse graph) is overhead we don't need once GROBID has already produced clean text; `instructor` gives the same "guaranteed schema" guarantee with far less surface area and clearer control over prompting/retries. |
| Chunking | Manual page-count chunking + multiprocessing + multi-pass refinement per material | Single-shot extraction per paper (DeepSeek's 64k-token context comfortably fits a full paper), with an optional per-material verification pass | Removes a large amount of bespoke chunking/process-pool code. The old pipeline's accuracy actually came from the *verification* pass, not the chunking, so that part is kept. |
| Schema | Two near-duplicate schemas (catalyst vs. adsorption pipelines) | Two schemas ported field-for-field from the original, experimentor-authored files: `catalyst_schema.py` (from `ldh_batch_pipeline_catalyst.py`) and `adsorption_schema.py` (from `patent_EVA_ldh_batch_pipeline_adsorption_simplified.py`) | Keeps the exact, already-validated data model for each pipeline instead of inventing a new unified one, while still dropping scrapegraphai/multiprocessing/chunking. |
| Resumability | Ad-hoc `run_context.json` + hand-maintained CSV backups | `<tag>_processed.json` manifest keyed by filename, skip-on-rerun | Same idea, simplified. |

## Setup

1. Install [pixi](https://pixi.sh) if you don't have it.
2. `cp .env.example .env`.
3. Fill in an API key in `.env` (see [LLM backend](#llm-backend) below) —
   the default `auto` provider needs `DASHSCOPE_API_KEY` on a MacBook, or
   nothing at all on an H100/H200 box (just `ollama pull`, see below).
4. Start GROBID: `pixi run grobid-up` (first pull takes a few minutes). On
   Apple Silicon Macs, Docker runs GROBID's image under x86_64 emulation
   (you'll see a harmless "platform does not match" warning), so it can
   take 2-3 minutes to finish loading its models on first start. Poll until
   ready:
   ```bash
   until curl -s -m 3 http://localhost:8070/api/isalive | grep -q true; do sleep 5; done
   echo "GROBID is ready"
   ```
5. `pixi install`

## Devcontainer (recommended for the H100/H200)

Modeled on the same `.devcontainer` pattern used in `PXR_Challenge` and
`ADX_DPPH`: a pixi-based container whose user matches your host UID/GID, bind
mounted so file changes sync live between the container and the host. The
only difference here is that `.devcontainer/build` picks the pixi base image
automatically:
- **MacBook / no GPU** → plain `ghcr.io/prefix-dev/pixi:0.41.4`.
- **H100/H200** (`nvidia-smi` detected) → CUDA-enabled
  `ghcr.io/prefix-dev/pixi:noble-cuda-12.8.1`, plus `--gpus all` so
  `nvidia-smi`/`ollama` inside the container see the GPU.

Override the guess with `GPU=1`/`GPU=0` (and `PIXI_IMAGE_TAG=...` to pin an
exact tag) before running the build script if needed.

**Selecting a GPU on a shared 8-GPU server:** set `GPU_DEVICE=3` (or
`GPU_DEVICE=2,3` for multiple) before running `./.devcontainer/build` to
pin the container to specific GPU indices (`--gpus device=...` instead of
`--gpus all`); it also falls back to `LITSCRAPER_GPU_DEVICE`/
`CUDA_VISIBLE_DEVICES` if already exported. Once inside the container, set
the same value as `LITSCRAPER_GPU_DEVICE` in `.env` so hardware detection
and Qwen3 model-sizing only look at that GPU, and `export
CUDA_VISIBLE_DEVICES=3` before `ollama serve` so Ollama itself only uses it.

**Quick start:**
1. SSH into the target machine (or open the folder locally on your Mac) and
   open this repo in VS Code.
2. `chmod +x ./.devcontainer/build`
3. `./.devcontainer/build` — generates `.devcontainer/devcontainer.json` from
   the template using your user info and detected hardware.
4. Command Palette → "Reopen in Container". You'll land in `/workspace` with
   `pixi install` already run. Any changes to files are reflected on the
   host machine and vice versa (it's a bind mount, not a copy).

**Reaching GROBID from inside the container:** the Docker CLI is
installed and the host's Docker socket is mounted, so `pixi run grobid-up`/
`grobid-down` still work unchanged — GROBID runs as a sibling container on
the host. Because of that, `localhost` inside the devcontainer is *not* the
same as the host's `localhost` for GROBID. Point `.env` at the host instead:
```
GROBID_URL=http://host.docker.internal:8070
```
(`host.docker.internal` is wired up via `--add-host` in the template, so this
works the same on the Mac and on Linux GPU boxes.)

Ollama itself is installed directly in the devcontainer image (CLI + server
binary), so `ollama serve`/`ollama pull` run inside the container and the
default `OLLAMA_BASE_URL=http://localhost:11434/v1` in `.env.example` just
works — no `host.docker.internal` needed for Ollama.

## LLM backend

This project is **Qwen-centric** and self-configures based on the machine
it runs on (`src/litscraper/hardware.py` detects GPU memory via
`nvidia-smi`), so the same `.env` works across your MacBook and an
H100/H200 server without editing code. Set `LITSCRAPER_LLM_PROVIDER` in
`.env` to override this if you want to force a specific backend.

**`auto` (default)**:
- **No large GPU detected (e.g. a MacBook)** → **Alibaba DashScope**, Qwen's
  hosted API. This is the only backend you need to set up on your personal
  Mac. Get a key from
  [bailian.console.alibabacloud.com](https://bailian.console.alibabacloud.com/)
  (Model Studio → API-KEY), then place it in `.env`:
  ```
  DASHSCOPE_API_KEY=sk-...
  ```
  That's it — everything else (`LITSCRAPER_LLM_PROVIDER=auto`,
  `DASHSCOPE_BASE_URL`, `LITSCRAPER_DASHSCOPE_MODEL=qwen3-235b-a22b`) is
  already set in `.env.example`. If your Alibaba Cloud account is
  mainland-China-based, swap `DASHSCOPE_BASE_URL` for the CN endpoint
  (commented in `.env.example`).
- **A large GPU detected (≥40GB, e.g. an H100/H200)** → **local Ollama**,
  no API key or per-token cost. The Qwen3 tag is auto-sized to the
  detected GPU memory (`qwen3:32b` on a single 80-141GB card, `qwen3:235b-a22b`
  on a multi-GPU node, smaller tags below that) unless you pin
  `LITSCRAPER_OLLAMA_MODEL` explicitly. In the `.devcontainer`, Ollama is
  already installed — just pull *a* Qwen3 model — run `pixi run python -m
  litscraper.hardware` to see which tag it picked, then:
  ```bash
  ollama pull qwen3:32b   # substitute the tag hardware.py reports
  ollama serve            # if not already running as a service
  ```
  (Outside the devcontainer, install Ollama yourself first: see
  [ollama.com/download](https://ollama.com/download).)
  On a shared server with GPUs 0-7, set `LITSCRAPER_GPU_DEVICE=3` (or
  `2,3` for several) in `.env` so detection/sizing only considers that
  GPU, and `export CUDA_VISIBLE_DEVICES=3` before `ollama serve` so Ollama
  itself is pinned to the same one(s) — otherwise Ollama may schedule
  onto whichever GPU it likes and sizing may assume more memory than
  you've actually been allocated.

Qwen3 is used for both backends because it has reliable native
tool-calling support, which `instructor` uses in `TOOLS` mode for strong
schema adherence on these deeply nested schemas.

**Forcing a backend** (skips auto-detection):
```
LITSCRAPER_LLM_PROVIDER=dashscope   # or: ollama, deepseek
```

**`deepseek`** — kept as a legacy/alternative hosted backend (this is what
the original pipeline used). DeepSeek's API doesn't support OpenAI-style
tool-calling strictly enough for `instructor`'s `TOOLS` mode, so this
backend uses `MD_JSON` mode (fenced-JSON prompting + validate/repair)
instead — slightly less reliable on deeply nested schemas than Qwen3's
native tool-calling.
```
LITSCRAPER_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...
```

## Usage

```bash
pixi run extract -- --pdf-dir /path/to/pdfs --out-dir outputs --tag most_relevant
```

This writes `outputs/most_relevant_adsorption.csv`, `outputs/most_relevant_catalyst.csv`,
and `outputs/most_relevant_processed.json`. Re-running with the same `--tag` skips
PDFs already recorded as processed; pass `--force` to redo everything.

## Testing

```bash
pixi run test
```

Tests cover TEI parsing, schema defaults/validation, and CSV row flattening.
They do not require GROBID or an API key to run.

## Layout

```
.devcontainer/
  Dockerfile                  # pixi base image (CPU or CUDA, picked by `build`)
  devcontainer.json.template    # templated devcontainer config
  build                          # generates devcontainer.json for this user/machine
src/litscraper/
  config.py              # env-driven settings
  hardware.py             # GPU-memory detection -> auto backend/model selection
  pdf_parsing/
    grobid_client.py      # talks to the GROBID docker service
    tei_parser.py          # TEI XML -> ParsedDocument (sections, tables, metadata)
  extraction/
    catalyst_schema.py       # Pydantic LDHCatalysisStudy / StudiesInPaper schema (ported from ldh_batch_pipeline_catalyst.py)
    adsorption_schema.py     # Pydantic AdsorptionMaterial schema (ported from patent_EVA_..._adsorption_simplified.py)
    prompts.py               # extraction + verification prompt templates for both passes
    llm_client.py             # auto/dashscope/ollama/deepseek client wrapped with `instructor`
    extractor.py               # per-paper orchestration: runs both the catalyst and adsorption passes
  pipeline/
    csv_writer.py               # LDHCatalysisStudy / AdsorptionMaterial -> CSV rows
    run.py                        # batch CLI entrypoint
```

Each PDF is run through two independent extraction passes (mirroring the
original project's separate catalyst/adsorption pipeline scripts): one using
the catalyst-focused `LDHCatalysisStudy` schema, one using the `AdsorptionMaterial`
schema. Each has its own prompt, its own optional row-level completeness
check, and its own optional per-material verification pass, and writes to
its own CSV.

**Row-level completeness check** (`LITSCRAPER_COMPLETENESS_CHECK=true`,
default): a "row" is one material-measurement pair — one material tested
under one specific condition (a material tested at 3 temperatures
contributes 3 rows). LLMs sometimes only extract a table's first or most
prominent row instead of every one. After the main extraction pass, a cheap
follow-up call asks the model to just enumerate every row it can find (no
full schema); if that count exceeds what was actually extracted, the full
extraction is retried once (`LITSCRAPER_COMPLETENESS_MAX_RETRIES`, default
`1`) with the missing rows spelled out explicitly, keeping whichever attempt
produced the most rows.
