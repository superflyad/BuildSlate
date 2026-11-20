"""Verify release versions and write the current changelog section."""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="release tag to verify")
    parser.add_argument("--notes-file", type=Path, help="write release notes here")
    args = parser.parse_args()

    metadata = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = metadata["project"]["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"invalid release version: {version}")
    viewer = json.loads((REPO_ROOT / "viewer/package.json").read_text(encoding="utf-8"))
    if viewer["version"] != version:
        raise SystemExit(f"viewer version {viewer['version']} differs from {version}")
    lock = json.loads(
        (REPO_ROOT / "viewer/package-lock.json").read_text(encoding="utf-8")
    )
    if lock["version"] != version or lock["packages"][""]["version"] != version:
        raise SystemExit(f"viewer lockfile version differs from {version}")
    if args.tag is not None and args.tag != f"v{version}":
        raise SystemExit(f"tag {args.tag} differs from v{version}")

    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(
        rf"(?ms)^## {re.escape(version)} - \d{{4}}-\d{{2}}-\d{{2}}\s*\n(.*?)(?=^## |\Z)",
        changelog,
    )
    if match is None or not match.group(1).strip():
        raise SystemExit(f"missing changelog entry for {version}")
    if args.notes_file:
        args.notes_file.write_text(match.group(1).strip() + "\n", encoding="utf-8")
    print(f"PASS: release v{version} has matching metadata and changelog")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
