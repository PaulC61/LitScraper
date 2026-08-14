"""Tests for GPU-memory-based backend/model selection in litscraper.hardware."""
from __future__ import annotations

from litscraper import hardware


def test_resolve_provider_returns_explicit_choice_unchanged():
    assert hardware.resolve_provider("deepseek") == "deepseek"
    assert hardware.resolve_provider("dashscope") == "dashscope"
    assert hardware.resolve_provider("ollama") == "ollama"


def test_resolve_provider_auto_picks_dashscope_below_threshold(monkeypatch):
    monkeypatch.setattr(hardware, "detect_gpu_memory_gb", lambda: 0.0)
    assert hardware.resolve_provider("auto") == "dashscope"


def test_resolve_provider_auto_picks_ollama_above_threshold(monkeypatch):
    monkeypatch.setattr(hardware, "detect_gpu_memory_gb", lambda: 80.0)
    assert hardware.resolve_provider("auto") == "ollama"


def test_select_ollama_model_tiers_by_memory():
    assert hardware.select_ollama_model(8.0) == "qwen3:8b"
    assert hardware.select_ollama_model(24.0) == "qwen3:14b"
    assert hardware.select_ollama_model(80.0) == "qwen3:32b"  # single H100/H200
    assert hardware.select_ollama_model(200.0) == "qwen3:235b-a22b"  # multi-GPU node


def test_detect_gpu_memory_gb_returns_float_without_crashing():
    # Whatever the actual machine has (0 on a MacBook, >0 on a GPU box),
    # this should never raise.
    assert isinstance(hardware.detect_gpu_memory_gb(), float)
