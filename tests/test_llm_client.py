"""Tests for LLM backend selection (auto/ollama/dashscope/deepseek), without
hitting any network or real GPU detection. We reload the config/llm_client
modules with patched env vars since `Settings` is a frozen dataclass
populated at import time, and we monkeypatch `hardware.detect_gpu_memory_gb`
to make "auto" resolution deterministic regardless of the machine running
the tests.
"""
from __future__ import annotations

import importlib
from types import SimpleNamespace


def _reload_with_env(monkeypatch, **env):
    for key in (
        "LITSCRAPER_LLM_PROVIDER", "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL",
        "LITSCRAPER_DEEPSEEK_MODEL", "OLLAMA_BASE_URL", "LITSCRAPER_OLLAMA_MODEL",
        "OLLAMA_API_KEY", "DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL",
        "LITSCRAPER_DASHSCOPE_MODEL", "LITSCRAPER_GPU_DEVICE", "CUDA_VISIBLE_DEVICES",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    from litscraper import config as config_module
    importlib.reload(config_module)
    from litscraper.extraction import llm_client as llm_client_module
    importlib.reload(llm_client_module)
    return config_module, llm_client_module


def test_defaults_to_auto(monkeypatch):
    config_module, _ = _reload_with_env(monkeypatch)
    assert config_module.settings.llm_provider == "auto"


def test_max_output_tokens_can_be_configured(monkeypatch):
    config_module, _ = _reload_with_env(monkeypatch, LITSCRAPER_MAX_OUTPUT_TOKENS="16384")
    assert config_module.settings.max_output_tokens == 16384

    config_module, _ = _reload_with_env(monkeypatch, LITSCRAPER_MAX_OUTPUT_TOKENS="32768")
    assert config_module.settings.max_output_tokens == 32768


def test_incomplete_output_retries_once_with_more_tokens(monkeypatch):
    _, llm_client_module = _reload_with_env(monkeypatch, LITSCRAPER_MAX_OUTPUT_TOKENS="8192")
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise llm_client_module.IncompleteOutputException()
        return "complete result"

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm_client_module, "resolved_provider", lambda: "ollama")
    monkeypatch.setattr(llm_client_module, "_model_name", lambda provider: "test-model")

    result = llm_client_module.extract_structured("prompt", object, client=client)

    assert result == "complete result"
    assert [call["max_tokens"] for call in calls] == [8192, 16384]


def test_auto_resolves_to_dashscope_without_a_large_gpu(monkeypatch):
    config_module, llm_client_module = _reload_with_env(
        monkeypatch, DASHSCOPE_API_KEY="sk-test"
    )
    monkeypatch.setattr(llm_client_module.hardware, "detect_gpu_memory_gb", lambda device=None: 0.0)
    assert llm_client_module.resolved_provider() == "dashscope"
    client = llm_client_module.get_client()
    assert client is not None
    assert llm_client_module._model_name() == config_module.settings.dashscope_model


def test_auto_resolves_to_ollama_with_a_large_gpu(monkeypatch):
    _, llm_client_module = _reload_with_env(monkeypatch)
    monkeypatch.setattr(llm_client_module.hardware, "detect_gpu_memory_gb", lambda device=None: 80.0)
    assert llm_client_module.resolved_provider() == "ollama"
    client = llm_client_module.get_client()
    assert client is not None
    # 80GB falls in the "single H100/H200" tier.
    assert llm_client_module._model_name() == "qwen3:32b"


def test_explicit_ollama_provider_via_env(monkeypatch):
    config_module, llm_client_module = _reload_with_env(
        monkeypatch, LITSCRAPER_LLM_PROVIDER="ollama", LITSCRAPER_OLLAMA_MODEL="qwen3:32b"
    )
    assert config_module.settings.llm_provider == "ollama"
    client = llm_client_module.get_client()
    assert client is not None
    assert llm_client_module._model_name() == "qwen3:32b"


def test_deepseek_provider_requires_api_key(monkeypatch):
    config_module, llm_client_module = _reload_with_env(
        monkeypatch, LITSCRAPER_LLM_PROVIDER="deepseek", DEEPSEEK_API_KEY=""
    )
    assert not config_module.settings.deepseek_api_key
    try:
        llm_client_module.get_client()
        assert False, "expected RuntimeError for missing DEEPSEEK_API_KEY"
    except RuntimeError as exc:
        assert "DEEPSEEK_API_KEY" in str(exc)


def test_dashscope_provider_requires_api_key(monkeypatch):
    config_module, llm_client_module = _reload_with_env(
        monkeypatch, LITSCRAPER_LLM_PROVIDER="dashscope", DASHSCOPE_API_KEY=""
    )
    assert not config_module.settings.dashscope_api_key
    try:
        llm_client_module.get_client()
        assert False, "expected RuntimeError for missing DASHSCOPE_API_KEY"
    except RuntimeError as exc:
        assert "DASHSCOPE_API_KEY" in str(exc)


def test_unknown_provider_raises(monkeypatch):
    _, llm_client_module = _reload_with_env(monkeypatch, LITSCRAPER_LLM_PROVIDER="bogus")
    try:
        llm_client_module.get_client()
        assert False, "expected ValueError for unknown provider"
    except ValueError as exc:
        assert "bogus" in str(exc)
