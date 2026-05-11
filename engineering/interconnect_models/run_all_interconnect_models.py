#!/usr/bin/env python3
"""Run all first-pass interconnect and power delivery models with default inputs."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


MODELS = (
    ("Memory bandwidth", "memory_bandwidth.py"),
    ("Power delivery", "power_delivery.py"),
    ("Routing density", "routing_density.py"),
    ("Package interconnect", "package_interconnect.py"),
    ("Power integrity", "power_integrity.py"),
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
