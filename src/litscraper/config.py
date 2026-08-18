"""Central configuration for the litscraper pipeline.

All tunables are read from environment variables (optionally loaded from a
.env file) so the same code works locally, in CI, or in a container without
code changes.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    # --- LLM backend selection ---
    # "auto" (default): pick automatically based on detected hardware (see
    #   litscraper.hardware) -> local Ollama Qwen3 on a big GPU box
    #   (H100/H200), Alibaba DashScope's hosted Qwen API otherwise (e.g. a
    #   MacBook with no NVIDIA GPU).
    # "ollama" / "dashscope" / "deepseek": force a specific backend.
    llm_provider: str = os.environ.get("LITSCRAPER_LLM_PROVIDER", "auto").strip().lower()

    # --- DeepSeek (OpenAI-compatible API) --- (legacy/alternative backend)
    deepseek_api_key: str | None = os.environ.get("DEEPSEEK_API_KEY")
    deepseek_base_url: str = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.environ.get("LITSCRAPER_DEEPSEEK_MODEL", "deepseek-chat")

    # --- Ollama (self-hosted, OpenAI-compatible API) ---
    # Used automatically on machines with a large GPU (e.g. H100/H200).
    # Leave LITSCRAPER_OLLAMA_MODEL unset to auto-size the Qwen3 tag to the
    # detected GPU memory (see litscraper.hardware.select_ollama_model).
    ollama_base_url: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    ollama_model: str | None = os.environ.get("LITSCRAPER_OLLAMA_MODEL") or None
    # Ollama ignores the API key but the OpenAI SDK requires a non-empty string.
    ollama_api_key: str = os.environ.get("OLLAMA_API_KEY", "ollama")

    # --- Alibaba DashScope (hosted Qwen API, OpenAI-compatible) ---
    # Used automatically on machines without a large GPU (e.g. a MacBook).
    # Get an API key from https://bailian.console.alibabacloud.com/
    # (Model Studio -> API-KEY) and place it in this project's .env file as
    # DASHSCOPE_API_KEY=sk-... (see .env.example).
    dashscope_api_key: str | None = os.environ.get("DASHSCOPE_API_KEY")
    dashscope_base_url: str = os.environ.get(
        "DASHSCOPE_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    )
    dashscope_model: str = os.environ.get("LITSCRAPER_DASHSCOPE_MODEL", "qwen3-235b-a22b")

    # --- GPU selection (shared multi-GPU servers, e.g. an 8x H100/H200 box) ---
    # Comma-separated GPU index/indices (e.g. "3" or "2,3") to pin both
    # hardware detection/model-sizing and (if you export it before `ollama
    # serve`) the actual Ollama process to specific GPU(s). Falls back to
    # the standard CUDA_VISIBLE_DEVICES if set. Leave unset to use/detect
    # all visible GPUs.
    gpu_device: str | None = os.environ.get("LITSCRAPER_GPU_DEVICE") or os.environ.get("CUDA_VISIBLE_DEVICES") or None

    # Large result tables need room for every nested measurement row; 8K can
    # truncate otherwise valid structured output before the JSON is complete.
    max_output_tokens: int = int(os.environ.get("LITSCRAPER_MAX_OUTPUT_TOKENS", "16384"))
    llm_max_retries: int = int(os.environ.get("LITSCRAPER_LLM_MAX_RETRIES", "3"))

    # --- GROBID ---
    grobid_url: str = os.environ.get("GROBID_URL", "http://localhost:8070")
    grobid_timeout_s: int = int(os.environ.get("GROBID_TIMEOUT_S", "180"))

    # --- Pipeline behavior ---
    do_verification_pass: bool = os.environ.get("LITSCRAPER_VERIFY", "true").lower() == "true"
    do_batch_assessment: bool = os.environ.get("LITSCRAPER_BATCH_ASSESS", "true").lower() == "true"
    cache_dir: str = os.environ.get("LITSCRAPER_CACHE_DIR", ".cache")


settings = Settings()
