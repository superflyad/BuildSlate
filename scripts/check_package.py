"""Build a wheel and exercise its CLI outside the source checkout."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=True)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="buildslate-package-") as directory:
        work = Path(directory)
        wheels = work / "wheels"
        wheels.mkdir()
        run(
            [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", str(wheels)],
            cwd=REPO_ROOT,
        )
        (wheel,) = wheels.glob("buildslate-*.whl")
        environment = work / "environment"
        venv.create(environment, with_pip=True)
        executable_dir = environment / ("Scripts" if sys.platform == "win32" else "bin")
        python = executable_dir / (
            "python.exe" if sys.platform == "win32" else "python"
        )
        cli = executable_dir / (
            "buildslate.exe" if sys.platform == "win32" else "buildslate"
        )
        run([str(python), "-m", "pip", "install", str(wheel)], cwd=work)

        command = ["--repo-root", str(REPO_ROOT), "status", "--format", "json"]
        for entry in (
            [str(cli), *command],
            [str(python), "-m", "buildslate", *command],
        ):
            result = run(entry, cwd=work)
            payload = json.loads(result.stdout)
            if payload.get("program_id") != "slate-pocket-v1r":
                raise AssertionError("installed CLI returned the wrong program")
        print("PASS: installed wheel CLI works outside the source checkout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
