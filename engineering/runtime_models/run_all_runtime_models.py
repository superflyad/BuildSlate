#!/usr/bin/env python3
"""Run all first-pass local AI runtime models with default inputs."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


MODELS = (
    ("Model residency", "model_residency.py"),
    ("KV cache", "kv_cache.py"),
    ("Context scaling", "context_scaling.py"),
    ("Model load time", "model_load_time.py"),
    ("Multimodal overhead", "multimodal_overhead.py"),
    ("Runtime memory budget", "runtime_memory_budget.py"),
)


def main() -> int:
    model_dir = Path(__file__).resolve().parent
    for title, script in MODELS:
        print("\n" + "=" * 72, flush=True)
        print(title, flush=True)
        print("=" * 72, flush=True)
        result = subprocess.run([sys.executable, str(model_dir / script)], check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
