#!/usr/bin/env python3
"""Validate repository wiring and local documentation links."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from validation.run_all import VALIDATION_CHECKS  # noqa: E402

LINK = re.compile(r"!?\[[^]]+\]\(([^)]+)\)")
PLACEHOLDER = "Placeholder directory for BuildSlate digital-twin artifacts."


def markdown_files() -> list[Path]:
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            "*.md",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    )
    files = {
        REPO_ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item
    }
    return sorted(path for path in files if path.is_file())


def validate_links(path: Path) -> list[str]:
    problems: list[str] = []
    content = path.read_text(encoding="utf-8")
    if path.name == "README.md" and PLACEHOLDER in content:
        problems.append(f"{path.relative_to(REPO_ROOT)}: placeholder README")
    for match in LINK.finditer(content):
        target = match.group(1).strip().split(" ", 1)[0].strip("<>")
        if not target or target.startswith("#") or urlsplit(target).scheme:
            continue
        relative = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if not relative:
            continue
        destination = (path.parent / relative).resolve()
        try:
            destination.relative_to(REPO_ROOT)
        except ValueError:
            problems.append(
                f"{path.relative_to(REPO_ROOT)}: link escapes repository: {target}"
            )
            continue
        if not destination.exists():
            problems.append(f"{path.relative_to(REPO_ROOT)}: broken link: {target}")
    return problems


def validate_document_index() -> list[str]:
    index = REPO_ROOT / "docs" / "README.md"
    listed: set[Path] = set()
    for match in LINK.finditer(index.read_text(encoding="utf-8")):
        target = match.group(1).strip().split(" ", 1)[0].strip("<>")
        if urlsplit(target).scheme:
            continue
        relative = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if relative:
            listed.add((index.parent / relative).resolve())
    required = {
        path.resolve()
        for folder in ("engineering", "standards")
        for path in (REPO_ROOT / "docs" / folder).glob("*.md")
    }
    return [
        f"docs/README.md: unlisted active guide: {path.relative_to(REPO_ROOT)}"
        for path in sorted(required - listed)
    ]


def main() -> int:
    scripts = {
        f"validation/{path.name}"
        for path in (REPO_ROOT / "validation").glob("validate_*.py")
    }
    registered = {
        entry for entry in VALIDATION_CHECKS if entry.startswith("validation/validate_")
    }
    problems = [
        f"unregistered validator: {path}" for path in sorted(scripts - registered)
    ]
    problems += [f"missing validator: {path}" for path in sorted(registered - scripts)]

    for requirements_file in ("requirements.txt", "requirements-dev.txt"):
        requirements = (
            (REPO_ROOT / requirements_file).read_text(encoding="utf-8").splitlines()
        )
        for requirement in requirements:
            requirement = requirement.strip()
            if (
                requirement
                and not requirement.startswith("#")
                and "==" not in requirement
            ):
                problems.append(
                    f"unpinned Python requirement in {requirements_file}: {requirement}"
                )

    documents = markdown_files()
    for path in documents:
        problems.extend(validate_links(path))
    problems.extend(validate_document_index())
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    print(
        f"PASS: {len(scripts)} registered validators, {len(documents)} Markdown files, local links, active guide index, and pinned Python requirements"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
