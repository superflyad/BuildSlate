#!/usr/bin/env python3
"""Validate configuration authority and dependency-aware regeneration."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from buildslate.configuration import ConfigurationResolver
from buildslate.io import load_yaml
from buildslate.regeneration import RegenerationEngine


def passed(message: str) -> None:
    print(f"PASS: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    passed(message)


def main() -> int:
    artifacts = (
        "engineering/program/configuration_registry.yaml",
        "engineering/program/regeneration.yaml",
        "reports/program/configuration-resolution.yaml",
        "reports/program/regeneration-state.yaml",
    )
    for artifact in artifacts:
        require((REPO_ROOT / artifact).is_file(), f"configuration automation artifact exists: {artifact}")

    resolver = ConfigurationResolver(REPO_ROOT)
    resolution = resolver.resolve()
    require(resolution["violations"] == [], "protected v1R profile has no configuration authority violations")
    require(resolution["CONFIGURATION_GATE"] == "CONTROLLED_WITH_UNRESOLVED_EXTERNAL_DECISIONS", "configuration gate preserves unresolved external decisions")
    require(resolution["classification_counts"]["operational_fallback"] == 4, "operational fallbacks are classified separately")
    require(resolution["classification_counts"]["rejected_option"] == 3, "rejected options remain traceable")
    require(resolution["classification_counts"].get("selected_component", 0) == 0, "no component selection is invented")
    require(load_yaml(REPO_ROOT / "reports/program/configuration-resolution.yaml") == resolution, "configuration resolution report is deterministic and current")

    with tempfile.TemporaryDirectory() as temp_directory:
        temporary_root = Path(temp_directory)
        for source in (
            "engineering/program/configuration_registry.yaml",
            "configs/devices/slate-pocket-v1r.yaml",
            "engineering/assumptions/assumption_registry.yaml",
        ):
            destination = temporary_root / source
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / source, destination)
        profile_path = temporary_root / "configs/devices/slate-pocket-v1r.yaml"
        profile = load_yaml(profile_path)
        profile["memory"]["capacity_gb"] = 256
        profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
        mutated = ConfigurationResolver(temporary_root).resolve()
        require(mutated["CONFIGURATION_GATE"] == "BLOCKED_UNSUPPORTED_CONFIGURATION", "authority mismatch blocks configuration")
        require(any(item["profile_path"] == "memory.capacity_gb" for item in mutated["violations"]), "unsupported downstream memory value is identified exactly")

    engine = RegenerationEngine(REPO_ROOT)
    require(engine.stale_nodes() == (), "all generated nodes match committed input and output hashes")
    profile_impact = engine.impacted_nodes(["configs/devices/slate-pocket-v1r.yaml"])
    require("configuration_resolution" in profile_impact and "program_snapshot" in profile_impact, "profile change propagates through configuration and program snapshot")
    supplier_impact = engine.impacted_nodes(["research/supplier-responses/receipts/example.yaml"])
    unaffected = set(engine.nodes) - set(supplier_impact)
    require(unaffected == {"migration_audit"}, "supplier receipt change propagates across every dependent engineering node")
    require(engine.impacted_nodes(["docs/unrelated-note.md"]) == (), "untracked path does not trigger unrelated generators")
    require(engine.load_state() == engine.build_state(), "regeneration state is deterministic and current")

    original_dependencies = list(engine.nodes["supplier_review"]["depends_on"])
    engine.nodes["supplier_review"]["depends_on"] = ["program_snapshot"]
    try:
        engine.topological_order()
    except ValueError as exc:
        require("cycle" in str(exc), "regeneration dependency cycles are rejected")
    else:
        raise AssertionError("regeneration cycle was not rejected")
    finally:
        engine.nodes["supplier_review"]["depends_on"] = original_dependencies

    with tempfile.TemporaryDirectory() as temp_directory:
        first = Path(temp_directory) / "first.txt"
        second = Path(temp_directory) / "second.txt"
        command = [sys.executable, "engineering/run_device_profile.py", "--profile", "configs/devices/slate-pocket-v1r.yaml"]
        first_run = subprocess.run(command + ["--output", str(first)], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        second_run = subprocess.run(command + ["--output", str(second)], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        require(first_run.returncode == 0 and second_run.returncode == 0, "device profile generator runs twice")
        require(first.read_bytes() == second.read_bytes(), "device profile output is byte-for-byte deterministic")

    cli = subprocess.run(
        [sys.executable, "-m", "buildslate", "impact", "--changed", "configs/devices/slate-pocket-v1r.yaml", "--format", "json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    require(cli.returncode == 0 and '"configuration_resolution"' in cli.stdout, "CLI exposes dependency impact")
    passed("configuration authority and regeneration validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

