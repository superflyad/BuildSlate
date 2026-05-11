#!/usr/bin/env python3
"""Run all first-pass component physics models with default inputs."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

MODEL_SCRIPTS = [
    'battery_pack.py',
    'display_module.py',
    'pcb_stack.py',
    'soc_package.py',
    'memory_package.py',
    'storage_package.py',
    'thermal_module.py',
    'camera_system.py',
    'antenna_rf.py',
    'wireless_charging.py',
    'structural_stackup.py',
]

def main() -> int:
    model_dir = Path(__file__).resolve().parent
    failures = 0
    print('Component physics model grouped report')
    print('These are screening models only; they do not claim production feasibility.')
    for script in MODEL_SCRIPTS:
        print('\n' + '=' * 78)
        print(f'MODEL: {script}')
        print('=' * 78)
        result = subprocess.run([sys.executable, str(model_dir / script)], check=False, text=True, capture_output=True)
        print(result.stdout, end='')
        if result.stderr:
            print('stderr:')
            print(result.stderr, end='')
        if result.returncode != 0:
            failures += 1
            print(f'ERROR: {script} exited with {result.returncode}')
    if failures:
        print(f'\ncompleted with {failures} model failure(s)')
        return 1
    print('\ncompleted all component models successfully')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
