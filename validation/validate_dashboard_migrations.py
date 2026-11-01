#!/usr/bin/env python3
"""Validate the program dashboard and legacy migration authority map."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from buildslate.dashboard import ProgramDashboard
from buildslate.io import load_yaml
from buildslate.migrations import MigrationRegistry
from buildslate.regeneration import RegenerationEngine


def passed(message: str) -> None:
    print(f"PASS: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    passed(message)


def main() -> int:
    dashboard_repository = ProgramDashboard(REPO_ROOT)
    dashboard = dashboard_repository.build()
    require(dashboard["DASHBOARD_GATE"] == "LOCAL_SYSTEM_CURRENT_EXTERNALLY_BLOCKED", "dashboard distinguishes local currency from external readiness")
    require(dashboard["summary"] == {
        "verified": 1,
        "available_not_verified": 3,
        "modeled_not_verified": 4,
        "rejected_options": 3,
        "stale_nodes": 0,
        "contradictions": 0,
        "external_blockers": 8,
    }, "dashboard preserves every required evidence class")
    require(len(dashboard["exact_next_actions"]) == 8, "every external blocker has an exact next action")
    require(all(item["authorization_required"] for item in dashboard["exact_next_actions"]), "every external next action retains its authorization boundary")
    require(load_yaml(REPO_ROOT / "reports/program/dashboard.yaml") == dashboard, "machine-readable dashboard is deterministic and current")
    markdown = (REPO_ROOT / "reports/program/dashboard.md").read_text(encoding="utf-8")
    require(markdown == dashboard_repository.render_markdown(dashboard), "human-readable dashboard is deterministic and current")
    for marker in ("Verified", "Available, not verified", "Modeled, not verified", "Rejected options", "Stale nodes", "Contradictions", "Exact externally blocked next actions"):
        require(marker in markdown, f"dashboard contains section: {marker}")

    migrations = MigrationRegistry(REPO_ROOT)
    audit = migrations.audit()
    require(audit["MIGRATION_GATE"] == "MIGRATION_MAP_VALID" and not audit["errors"], "migration authority and compatibility map is valid")
    require(audit["duplicate_authority"] == {}, "migration map has no duplicated authority")
    require(load_yaml(REPO_ROOT / "reports/program/migration-audit.yaml") == audit, "migration audit is deterministic and current")
    evt0_legacy = migrations.explain("legacy_evt0_results")
    require(evt0_legacy["replacement"] == "validation/evt0/campaigns" and evt0_legacy["migration_command"], "legacy EVT0 intake has an explicit replacement and command")
    pilot_legacy = migrations.explain("legacy_pilot_results")
    require(pilot_legacy["replacement"] == "manufacturing/pilot-results/campaigns" and pilot_legacy["migration_command"], "legacy pilot intake has an explicit replacement and command")

    duplicate = dict(migrations.registry["artifacts"]["risk_register"])
    migrations.registry["artifacts"]["duplicate-risk-authority"] = duplicate
    require(bool(migrations.audit()["duplicate_authority"]), "migration audit rejects duplicated authority")

    require(RegenerationEngine(REPO_ROOT).stale_nodes() == (), "dashboard and migration outputs participate in clean regeneration state")
    cli = subprocess.run(
        [sys.executable, "-m", "buildslate", "dashboard", "--format", "json"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    require(cli.returncode == 0 and '"external_blockers": 8' in cli.stdout, "CLI exposes the consolidated program dashboard")
    passed("dashboard and migration validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

