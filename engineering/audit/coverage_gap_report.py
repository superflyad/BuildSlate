#!/usr/bin/env python3
"""Generate a markdown coverage gap report from the engineering audit registry."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from validation.validate_coverage_registry import load_registry, validate_registry  # noqa: E402

REPORT_PATH = REPO_ROOT / "reports" / "audit" / "coverage-gap-report.md"


def backend_readiness_verdict(entries: list[dict[str, Any]]) -> str:
    counts = Counter(entry["coverage_status"] for entry in entries)
    maturity = Counter(entry["maturity_level"] for entry in entries)
    critical_open = any(
        entry["review_priority"] == "critical"
        and (entry["coverage_status"] in {"weak", "missing"} or entry["maturity_level"] == "screening")
        for entry in entries
    )

    if counts.get("missing", 0) > 0:
        return "not_ready"
    if critical_open or counts.get("weak", 0) > 0 or maturity.get("screening", 0) > 0:
        return "screening_ready"
    if counts.get("partial", 0) > 0 or maturity.get("first_order", 0) > 0:
        return "profile_ready"
    if maturity.get("calibrated", 0) > 0 and maturity.get("validated", 0) == 0:
        return "report_ready"
    return "externally_review_ready"


def domain_table(entries: list[dict[str, Any]]) -> list[str]:
    if not entries:
        return ["No domains in this section.", ""]
    lines = ["| Domain | Maturity | Priority | Known gaps |", "| --- | --- | --- | --- |"]
    for entry in entries:
        gaps = "; ".join(entry["known_gaps"])
        lines.append(
            f"| `{entry['domain']}` | {entry['maturity_level']} | {entry['review_priority']} | {gaps} |"
        )
    lines.append("")
    return lines


def evidence_lines(entries: list[dict[str, Any]]) -> list[str]:
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_entries = sorted(entries, key=lambda entry: (priority_order[entry["review_priority"]], entry["domain"]))
    lines: list[str] = []
    for entry in sorted_entries:
        evidence = "; ".join(entry["required_next_evidence"])
        lines.append(f"- **{entry['domain']}** ({entry['review_priority']}): {evidence}")
    lines.append("")
    return lines


def build_report(entries: list[dict[str, Any]]) -> str:
    coverage_counts = Counter(entry["coverage_status"] for entry in entries)
    maturity_counts = Counter(entry["maturity_level"] for entry in entries)
    verdict = backend_readiness_verdict(entries)
    sections: list[str] = [
        "# BuildSlate Coverage Gap Report",
        "",
        "## Executive Summary",
        "",
        f"- Total audited domains: **{len(entries)}**",
        f"- Coverage counts: covered={coverage_counts.get('covered', 0)}, partial={coverage_counts.get('partial', 0)}, weak={coverage_counts.get('weak', 0)}, missing={coverage_counts.get('missing', 0)}",
        f"- Maturity counts: screening={maturity_counts.get('screening', 0)}, first_order={maturity_counts.get('first_order', 0)}, calibrated={maturity_counts.get('calibrated', 0)}, validated={maturity_counts.get('validated', 0)}",
        f"- Backend readiness verdict: **{verdict}**",
        "- This report is a conservative engineering screening artifact. It does not claim production validation or external review readiness.",
        "",
    ]

    for title, status in (
        ("Covered Domains", "covered"),
        ("Partial Domains", "partial"),
        ("Weak Domains", "weak"),
        ("Missing Domains", "missing"),
    ):
        sections.extend([f"## {title}", ""])
        sections.extend(domain_table([entry for entry in entries if entry["coverage_status"] == status]))

    critical_entries = [entry for entry in entries if entry["review_priority"] == "critical"]
    sections.extend(["## Critical Review Priorities", ""])
    sections.extend(domain_table(critical_entries))

    sections.extend(["## Required Next Evidence", ""])
    sections.extend(evidence_lines(entries))

    sections.extend(
        [
            "## Backend Readiness Verdict",
            "",
            f"**{verdict}**",
            "",
            "The backend is suitable for conservative screening and profile-level gap discovery, but it is not externally review ready. Critical thermal, power, routing, RF, stackup, manufacturing, and sustained-performance domains still need measured data, supplier references, CAD evidence, simulation, or prototype validation before higher-level automation can present outputs as mature engineering conclusions.",
            "",
        ]
    )
    return "\n".join(sections)


def main() -> int:
    try:
        registry = load_registry()
        entries = validate_registry(registry)
    except Exception as exc:  # noqa: BLE001 - CLI should return a clear validation failure.
        print(f"FAIL: coverage gap report failed: {exc}")
        return 1

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_report(entries), encoding="utf-8")
    print(f"PASS: wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(f"Backend readiness verdict: {backend_readiness_verdict(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
