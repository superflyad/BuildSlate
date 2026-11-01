#!/usr/bin/env python3
"""Validate Phase 2 integration contracts and contradiction blocking."""

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

from buildslate.contracts import IntegrationContractRepository
from buildslate.io import load_yaml
from buildslate.regeneration import RegenerationEngine


def passed(message: str) -> None:
    print(f"PASS: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    passed(message)


def main() -> int:
    repository = IntegrationContractRepository(REPO_ROOT)
    result = repository.evaluate()
    require(set(result["domain_statuses"]) == {"mechanical", "ecad", "power", "thermal", "rf", "firmware", "manufacturing"}, "contracts cover all seven Phase 2 domains")
    require(result["check_count"] >= 20, "cross-domain consistency matrix is substantive")
    require(result["contradictions"] == [], "protected baseline has no cross-domain contradictions")
    require(result["INTEGRATION_CONTRACT_GATE"] == "CONTRACTS_CONSISTENT_NOT_RELEASED", "consistent provisional contracts do not claim release")
    require(load_yaml(REPO_ROOT / "reports/program/integration-contracts.yaml") == result, "integration contract report is deterministic and current")

    manifest = load_yaml(REPO_ROOT / "engineering/program/integration_contracts.yaml")
    with tempfile.TemporaryDirectory() as temp_directory:
        temporary_root = Path(temp_directory)
        files = {"engineering/program/integration_contracts.yaml"}
        for contract in manifest["domains"].values():
            files.update(contract["inputs"])
            files.update(contract["outputs"])
        for relative in files:
            destination = temporary_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / relative, destination)
        thermal_path = temporary_root / "simulations/thermal/slate-pocket-v1r/model/model.yaml"
        thermal = load_yaml(thermal_path)
        thermal["heat_sources"]["compute_soc"]["sustained_w"] = 27.0
        thermal_path.write_text(yaml.safe_dump(thermal, sort_keys=False), encoding="utf-8")
        contradicted = IntegrationContractRepository(temporary_root).evaluate()
        require(contradicted["INTEGRATION_CONTRACT_GATE"] == "BLOCKED_CROSS_DOMAIN_CONTRADICTION", "cross-domain drift blocks the integration gate")
        require(any(item["id"] == "thermal_compute_sustained" for item in contradicted["contradictions"]), "contradiction identifies the exact interface")

    engine = RegenerationEngine(REPO_ROOT)
    impact = engine.impacted_nodes(["engineering/pcb/power-tree.yaml"])
    require("integration_contracts" in impact and "thermal_readiness" in impact and "program_snapshot" in impact, "contract input change propagates through dependent outputs")

    cli = subprocess.run(
        [sys.executable, "-m", "buildslate", "contracts", "validate", "--format", "json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    require(cli.returncode == 0 and '"contradiction_count": 0' in cli.stdout, "CLI exposes integration contract status")
    passed("Phase 2 integration contract validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

