#!/usr/bin/env python3
"""Record the inference stack on the MSI machine (run there, before the engineering pilot).

Usage: python scripts/msi/record_env.py --out manifests/msi_env.json
Records Python, torch, vllm, transformers versions (if importable in this interpreter; run it in
the vLLM venv too), CUDA availability and device capability, nvidia-smi output, and the pinned
model revision from configs/msi/qwen3_8b.yaml. Contains no secrets.
"""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def version(mod: str) -> str | None:
    try:
        return getattr(importlib.import_module(mod), "__version__", "unknown")
    except ImportError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="manifests/msi_env.json")
    args = ap.parse_args()
    env: dict = {
        "python": sys.version,
        "platform": platform.platform(),
        "packages": {m: version(m) for m in ("torch", "vllm", "transformers")},
    }
    try:
        import torch

        env["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            env["device_name"] = torch.cuda.get_device_name(0)
            env["device_capability"] = list(torch.cuda.get_device_capability(0))
            env["torch_cuda"] = torch.version.cuda
    except ImportError:
        env["cuda_available"] = None
    try:
        env["nvidia_smi"] = subprocess.run(
            ["nvidia-smi"], capture_output=True, text=True, timeout=20
        ).stdout[:3000]
    except (OSError, subprocess.SubprocessError) as err:
        env["nvidia_smi"] = f"unavailable: {err}"
    cfg = yaml.safe_load((ROOT / "configs/msi/qwen3_8b.yaml").read_text(encoding="utf-8"))
    env["model"] = cfg["model"]
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(env, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: env[k] for k in ("packages", "cuda_available")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
