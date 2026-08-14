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

**Selecting specific GPU(s) on a shared multi-GPU server:** the H100/H200
box has 8 GPUs (indices 0-7) shared across users/jobs. Set
`LITSCRAPER_GPU_DEVICE` in `.env` (or the standard `CUDA_VISIBLE_DEVICES`)
to a comma-separated list of indices, e.g. `LITSCRAPER_GPU_DEVICE=3` or
`LITSCRAPER_GPU_DEVICE=2,3`, to restrict both hardware detection *and*
model sizing to just those GPUs, so `qwen3:*` isn't sized as if all 8 GPUs
were available. `nvidia-smi` itself ignores `CUDA_VISIBLE_DEVICES` (that
only affects CUDA applications), so detection here explicitly filters by
`-i` to stay consistent with whichever device(s) you've pinned.
"""
from __future__ import annotations

import functools
import os
import subprocess

# Below this much total GPU memory, we assume the machine can't comfortably
# serve a useful local Qwen3 model and should fall back to the hosted API.
OLLAMA_GPU_THRESHOLD_GB = 40.0


def _configured_device() -> str | None:
    """The GPU index/indices pinned via .env, if any (see module docstring)."""
    device = os.environ.get("LITSCRAPER_GPU_DEVICE") or os.environ.get("CUDA_VISIBLE_DEVICES")
    device = (device or "").strip()
    return device or None


@functools.lru_cache(maxsize=8)
def _detect_gpu_memory_gb_cached(device: str | None) -> float:
    command = ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"]
    if device:
        command += ["-i", device]
    try:
        result = subprocess.run(
            command,
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


def detect_gpu_memory_gb(device: str | None = None) -> float:
    """Return total NVIDIA GPU memory in GiB, restricted to `device` if given
    (comma-separated indices, e.g. "0" or "2,3"), else `LITSCRAPER_GPU_DEVICE`
    / `CUDA_VISIBLE_DEVICES` from the environment, else all visible GPUs.

    Returns 0.0 if `nvidia-smi` isn't available or reports no GPUs (e.g. on
    a MacBook), or if detection fails for any other reason.
    """
    if device is None:
        device = _configured_device()
    return _detect_gpu_memory_gb_cached(device)


def resolve_provider(configured_provider: str, device: str | None = None) -> str:
    """Resolve "auto" to a concrete provider based on detected hardware.

    A non-"auto" value is returned unchanged (explicit user choice wins).
    """
    if configured_provider != "auto":
        return configured_provider
    gpu_gb = detect_gpu_memory_gb(device)
    return "ollama" if gpu_gb >= OLLAMA_GPU_THRESHOLD_GB else "dashscope"


def select_ollama_model(gpu_gb: float | None = None, device: str | None = None) -> str:
    """Pick a Qwen3 Ollama tag sized to fit the detected GPU memory.

    Thresholds are rough rules of thumb for weights + KV cache headroom,
    not exact memory accounting.
    """
    if gpu_gb is None:
        gpu_gb = detect_gpu_memory_gb(device)
    if gpu_gb >= 180:
        return "qwen3:235b-a22b"  # multi-GPU H100/H200 nodes (e.g. 2-8x GPUs)
    if gpu_gb >= 60:
        return "qwen3:32b"  # single H100 (80GB) / H200 (141GB)
    if gpu_gb >= 24:
        return "qwen3:14b"
    return "qwen3:8b"


def describe(device: str | None = None) -> str:
    """Human-readable summary of detected hardware and the resulting choice,
    useful for logging/diagnostics."""
    if device is None:
        device = _configured_device()
    gpu_gb = detect_gpu_memory_gb(device)
    device_note = f" (device={device})" if device else ""
    if gpu_gb >= OLLAMA_GPU_THRESHOLD_GB:
        model = select_ollama_model(gpu_gb)
        return f"Detected {gpu_gb:.0f}GB GPU memory{device_note} -> local Ollama backend, model={model}"
    return (
        f"Detected {gpu_gb:.0f}GB GPU memory{device_note} "
        f"(below {OLLAMA_GPU_THRESHOLD_GB:.0f}GB threshold) -> Alibaba DashScope (Qwen API) backend"
    )


if __name__ == "__main__":
    print(describe())
