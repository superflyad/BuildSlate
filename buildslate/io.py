"""Deterministic file loading and serialization helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping with a stable, actionable error."""
    if not path.exists():
        raise ValueError(f"file does not exist: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def dump_yaml(data: Any) -> str:
    """Serialize YAML deterministically for generated artifacts."""
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=120)


def dump_json(data: Any) -> str:
    """Serialize JSON deterministically for CLI consumers."""
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, default=str)
