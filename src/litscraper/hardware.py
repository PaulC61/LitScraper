"""Hardware detection for auto-selecting an LLM backend/model.

Goal: this project is Qwen-centric and should "just work" on either of the
two machines it's used on, with no manual flipping of settings:

  * A personal MacBook (no NVIDIA GPU) -> Alibaba's hosted Qwen API
    (DashScope), since there isn't enough local memory/compute to run a
    capable Qwen3 model well.
  * An H100/H200 GPU server (80GB-141GB+ of GPU memory) -> a local,
    Ollama-served Qwen3 model, sized to fit comfortably in the detected
    GPU memory.

Detection is done by shelling out to `nvidia-smi`, which is present on any
machine with the NVIDIA driver installed (including GPU servers) and absent
on a Mac. This keeps things simple and dependency-free (no torch/pynvml
requirement just to pick a backend).
"""
from __future__ import annotations

import functools
import subprocess

# Below this much total GPU memory, we assume the machine can't comfortably
# serve a useful local Qwen3 model and should fall back to the hosted API.
OLLAMA_GPU_THRESHOLD_GB = 40.0


@functools.lru_cache(maxsize=1)
def detect_gpu_memory_gb() -> float:
    """Return total NVIDIA GPU memory across all visible GPUs, in GiB.

    Returns 0.0 if `nvidia-smi` isn't available or reports no GPUs (e.g. on
    a MacBook), or if detection fails for any other reason.
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return 0.0

    total_mib = 0.0
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            total_mib += float(line)
        except ValueError:
            continue
    return total_mib / 1024.0


def resolve_provider(configured_provider: str) -> str:
    """Resolve "auto" to a concrete provider based on detected hardware.

    A non-"auto" value is returned unchanged (explicit user choice wins).
    """
    if configured_provider != "auto":
        return configured_provider
    gpu_gb = detect_gpu_memory_gb()
    return "ollama" if gpu_gb >= OLLAMA_GPU_THRESHOLD_GB else "dashscope"


def select_ollama_model(gpu_gb: float | None = None) -> str:
    """Pick a Qwen3 Ollama tag sized to fit the detected GPU memory.

    Thresholds are rough rules of thumb for weights + KV cache headroom,
    not exact memory accounting.
    """
    if gpu_gb is None:
        gpu_gb = detect_gpu_memory_gb()
    if gpu_gb >= 180:
        return "qwen3:235b-a22b"  # multi-GPU H100/H200 nodes (e.g. 2-8x GPUs)
    if gpu_gb >= 60:
        return "qwen3:32b"  # single H100 (80GB) / H200 (141GB)
    if gpu_gb >= 24:
        return "qwen3:14b"
    return "qwen3:8b"


def describe() -> str:
    """Human-readable summary of detected hardware and the resulting choice,
    useful for logging/diagnostics."""
    gpu_gb = detect_gpu_memory_gb()
    if gpu_gb >= OLLAMA_GPU_THRESHOLD_GB:
        model = select_ollama_model(gpu_gb)
        return f"Detected {gpu_gb:.0f}GB GPU memory -> local Ollama backend, model={model}"
    return f"Detected {gpu_gb:.0f}GB GPU memory (below {OLLAMA_GPU_THRESHOLD_GB:.0f}GB threshold) -> Alibaba DashScope (Qwen API) backend"


if __name__ == "__main__":
    print(describe())
