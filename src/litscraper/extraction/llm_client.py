"""LLM client wrapper: a configurable, auto-detecting backend, all patched
with `instructor` for guaranteed Pydantic-schema-validated structured
outputs.

This replaces scrapegraphai's SmartScraperGraph. scrapegraphai is designed
around web-scraping graphs (fetch -> render -> parse -> extract) which adds
orchestration overhead we don't need here, since PDF parsing is already
handled by GROBID upstream. `instructor` gives the same "structured output"
guarantee (schema validation with automatic re-prompt-on-failure retries)
with a much smaller surface area and direct control over prompts/retries,
and it works the same way regardless of which OpenAI-compatible backend is
selected below.

This project is Qwen-centric and auto-selects a backend based on the
machine it's running on (see `litscraper.hardware`), so the same codebase
works unchanged on a MacBook and on an H100/H200 server:

  * "auto" (default, `LITSCRAPER_LLM_PROVIDER=auto`):
      - Large GPU detected (e.g. H100/H200) -> "ollama": a local Qwen3
        model served by Ollama, sized to the detected GPU memory.
      - No/small GPU (e.g. a MacBook) -> "dashscope": Alibaba's hosted
        Qwen API.
  * "ollama": force the local Ollama backend. Qwen3 has reliable native
    tool-calling support, so we use instructor's TOOLS mode.
  * "dashscope": force Alibaba's hosted Qwen API (OpenAI-compatible). Also
    uses TOOLS mode (Qwen3 supports function calling there too).
  * "deepseek": legacy/alternative hosted backend. DeepSeek's chat API
    doesn't support OpenAI-style tool-calling strictly enough for
    instructor's TOOLS mode, so we use instructor's MD_JSON mode instead
    (fenced-JSON prompting + validate/repair).
"""
from __future__ import annotations

import logging
import time

import instructor
import openai
from instructor.core.exceptions import IncompleteOutputException
from pydantic import BaseModel

from litscraper import hardware
from litscraper.config import settings

logger = logging.getLogger(__name__)

# Errors that are worth re-sending the whole request for: the model never
# produced a usable response, but the backend itself is probably still fine.
RETRYABLE_ERRORS = (
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.InternalServerError,
    openai.RateLimitError,
)


def resolved_provider() -> str:
    """The concrete provider actually in effect, after resolving "auto"."""
    return hardware.resolve_provider(settings.llm_provider, device=settings.gpu_device)


def get_client() -> instructor.Instructor:
    provider = resolved_provider()

    if provider == "ollama":
        raw_client = openai.OpenAI(
            api_key=settings.ollama_api_key,
            base_url=settings.ollama_base_url,
            timeout=settings.llm_timeout_s,
            max_retries=settings.llm_transport_retries,
        )
        return instructor.from_openai(raw_client, mode=instructor.Mode.TOOLS)

    if provider == "dashscope":
        if not settings.dashscope_api_key:
            raise RuntimeError(
                "DASHSCOPE_API_KEY is not set. Get one from "
                "https://bailian.console.alibabacloud.com/ (Model Studio -> "
                "API-KEY) and add it to your .env file."
            )
        raw_client = openai.OpenAI(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            timeout=settings.llm_timeout_s,
            max_retries=settings.llm_transport_retries,
        )
        return instructor.from_openai(raw_client, mode=instructor.Mode.TOOLS)

    if provider == "deepseek":
        if not settings.deepseek_api_key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY is not set. Add it to your environment or a .env file."
            )
        raw_client = openai.OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=settings.llm_timeout_s,
            max_retries=settings.llm_transport_retries,
        )
        return instructor.from_openai(raw_client, mode=instructor.Mode.MD_JSON)

    raise ValueError(
        f"Unknown LITSCRAPER_LLM_PROVIDER={settings.llm_provider!r}; "
        "expected 'auto', 'ollama', 'dashscope', or 'deepseek'."
    )


def _model_name(provider: str | None = None) -> str:
    provider = provider or resolved_provider()
    if provider == "ollama":
        return settings.ollama_model or hardware.select_ollama_model(device=settings.gpu_device)
    if provider == "dashscope":
        return settings.dashscope_model
    if provider == "deepseek":
        return settings.deepseek_model
    raise ValueError(f"Unknown provider {provider!r}")


def _extra_body(provider: str) -> dict:
    """Provider-specific request tweaks that aren't part of the OpenAI API.

    Qwen3 models on DashScope default to "thinking mode", which only
    supports streaming responses and is incompatible with instructor's
    forced tool-calling (`tool_choice=required`) in non-streaming mode. We
    extract structured data in one shot rather than streaming, so thinking
    mode must be explicitly disabled for the dashscope backend.
    """
    if provider == "dashscope":
        return {"enable_thinking": False}
    return {}


def extract_structured(
    prompt: str,
    response_model: type[BaseModel],
    client: instructor.Instructor | None = None,
) -> BaseModel:
    """Send `prompt` to the configured LLM backend and return a validated
    instance of `response_model`.

    instructor automatically retries with the validation error fed back to
    the model if the first response doesn't satisfy the schema; timeouts and
    transient backend failures are retried here with exponential backoff.
    """
    provider = resolved_provider()
    client = client or get_client()
    request = {
        "model": _model_name(provider),
        "max_tokens": settings.max_output_tokens,
        "max_retries": settings.llm_max_retries,
        "messages": [{"role": "user", "content": prompt}],
        "response_model": response_model,
        "extra_body": _extra_body(provider),
    }
    try:
        return _create_with_retries(client, request)
    except IncompleteOutputException:
        recovery_max_tokens = min(max(settings.max_output_tokens * 2, 16384), 32768)
        if recovery_max_tokens <= settings.max_output_tokens:
            raise
        logger.warning(
            "Structured output reached the %d-token limit; retrying once with %d tokens",
            settings.max_output_tokens,
            recovery_max_tokens,
        )
        return _create_with_retries(client, {**request, "max_tokens": recovery_max_tokens})


def _create_with_retries(client: instructor.Instructor, request: dict) -> BaseModel:
    attempts = max(settings.llm_timeout_retries, 0) + 1
    for attempt in range(1, attempts + 1):
        try:
            return client.chat.completions.create(**request)
        except RETRYABLE_ERRORS as exc:
            if attempt == attempts:
                raise
            delay = settings.llm_retry_backoff_s * (2 ** (attempt - 1))
            logger.warning(
                "LLM request failed (%s: %s); retry %d/%d in %.0fs",
                type(exc).__name__, exc, attempt, attempts - 1, delay,
            )
            time.sleep(delay)
    raise AssertionError("unreachable")
