#!/usr/bin/env python3
"""Generate the Slate Pocket evidence readiness report."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.evidence.evidence_engine import (  # noqa: E402
    REGISTRY_PATH,
    EvidencePackage,
    build_packages,
    load_registry,
    readiness_decision,
    status_counts,
    unblocked_packages,
)

REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-evidence-readiness.txt"


def _render_package(package: EvidencePackage) -> list[str]:
    dependencies = ", ".join(package.depends_on) if package.depends_on else "none"
    return [
        f"  - {package.package_id}: {package.title}",
        f"    priority: {package.priority}",
        f"    status: {package.status}",
        f"    owner: {package.owner}",
        f"    depends_on: {dependencies}",
        f"    linked_risks: {', '.join(package.linked_risks)}",
        "    acceptance criteria:",
        *[f"      - {criterion}" for criterion in package.acceptance_criteria],
        "    expected artifacts:",
        *[f"      - {artifact}" for artifact in package.expected_artifacts],
        f"    notes: {package.notes}",
    ]


def render_report(packages: tuple[EvidencePackage, ...], caveat: str) -> str:
    """Render the evidence readiness report."""
    decision = readiness_decision(packages)
    counts = status_counts(packages)
    verified_count = counts["verified"]
    critical_open = [
        package for package in packages if package.priority == "critical" and not package.is_verified
    ]
    ready_now = unblocked_packages(packages)

    lines = [
        "Slate Pocket Evidence Readiness Gate v1",
        "========================================",
        "",
        "Executive summary:",
        "  baseline profile: slate-pocket-v1r",
        f"  evidence packages: {len(packages)}",
        f"  verified packages: {verified_count}/{len(packages)}",
        (
            "  status counts: "
            + ", ".join(f"{status}={counts[status]}" for status in ("missing", "planned", "in_progress", "available", "verified"))
        ),
        f"  open critical packages: {len(critical_open)}",
        f"  EVIDENCE_DECISION: {decision.value}",
        f"  registry source: {REGISTRY_PATH.relative_to(REPO_ROOT)}",
        "",
        "Attack now:",
    ]
    for package in ready_now:
        lines.extend(
            [
                f"  - {package.package_id} ({package.priority}, {package.status})",
                f"    {package.title}",
            ]
        )

    grouped: dict[int, list[EvidencePackage]] = defaultdict(list)
    for package in packages:
        grouped[package.phase].append(package)
    for phase in sorted(grouped):
        lines.extend(["", f"Phase {phase} evidence packages:"])
        for package in grouped[phase]:
            lines.extend(_render_package(package))

    lines.extend(
        [
            "",
            "Gate rules:",
            "  - An artifact must be reviewed against every acceptance criterion before status can become verified.",
            "  - Foundational critical packages in phases 0-2 must be verified before the prototype gate opens.",
            "  - An owner is required before a package can move to in_progress, available, or verified.",
            "  - Requirement changes must update linked specs, assumptions, risks, and dependent evidence packages.",
            "",
            "Caveat:",
            f"  {caveat.strip()}",
            "",
        ]
    )
    return "\n".join(lines)


def build_report() -> str:
    """Build the evidence readiness report from the registry."""
    registry = load_registry()
    return render_report(build_packages(registry), registry["caveat"])


def main() -> int:
    report = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
