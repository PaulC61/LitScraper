"""Tests for GPU-memory-based backend/model selection in litscraper.hardware."""
from __future__ import annotations

from litscraper import hardware


def test_resolve_provider_returns_explicit_choice_unchanged():
    assert hardware.resolve_provider("deepseek") == "deepseek"
    assert hardware.resolve_provider("dashscope") == "dashscope"
    assert hardware.resolve_provider("ollama") == "ollama"


def test_resolve_provider_auto_picks_dashscope_below_threshold(monkeypatch):
    monkeypatch.setattr(hardware, "detect_gpu_memory_gb", lambda device=None: 0.0)
    assert hardware.resolve_provider("auto") == "dashscope"


def test_resolve_provider_auto_picks_ollama_above_threshold(monkeypatch):
    monkeypatch.setattr(hardware, "detect_gpu_memory_gb", lambda device=None: 80.0)
    assert hardware.resolve_provider("auto") == "ollama"


def test_select_ollama_model_tiers_by_memory():
    assert hardware.select_ollama_model(8.0) == "qwen3:8b"
    assert hardware.select_ollama_model(24.0) == "qwen3:14b"
    assert hardware.select_ollama_model(80.0) == "qwen3:32b"  # single H100/H200
    assert hardware.select_ollama_model(200.0) == "qwen3:235b-a22b"  # multi-GPU node


def test_detect_gpu_memory_gb_accepts_device_arg_without_crashing():
    # A pinned device (real or bogus) should never raise; it just narrows
    # (or, on a MacBook, still returns 0.0) what nvidia-smi is asked about.
    assert isinstance(hardware.detect_gpu_memory_gb(device="0"), float)
    assert isinstance(hardware.detect_gpu_memory_gb(device="0,1"), float)


def test_configured_device_reads_litscraper_gpu_device_env(monkeypatch):
    monkeypatch.setenv("LITSCRAPER_GPU_DEVICE", "3")
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    assert hardware._configured_device() == "3"


def test_configured_device_falls_back_to_cuda_visible_devices(monkeypatch):
    monkeypatch.delenv("LITSCRAPER_GPU_DEVICE", raising=False)
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "2,3")
    assert hardware._configured_device() == "2,3"


def test_configured_device_none_when_unset(monkeypatch):
    monkeypatch.delenv("LITSCRAPER_GPU_DEVICE", raising=False)
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    assert hardware._configured_device() is None


def test_resolve_provider_and_select_model_accept_explicit_device(monkeypatch):
    monkeypatch.setattr(hardware, "detect_gpu_memory_gb", lambda device=None: 80.0 if device == "0" else 0.0)
    assert hardware.resolve_provider("auto", device="0") == "ollama"
    assert hardware.resolve_provider("auto", device="1") == "dashscope"
    assert hardware.select_ollama_model(device="0") == "qwen3:32b"


def test_detect_gpu_memory_gb_returns_float_without_crashing():
    # Whatever the actual machine has (0 on a MacBook, >0 on a GPU box),
    # this should never raise.
    assert isinstance(hardware.detect_gpu_memory_gb(), float)
