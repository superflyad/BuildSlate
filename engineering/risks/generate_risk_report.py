#!/usr/bin/env python3
"""Generate the Slate Pocket engineering risk register report."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.risks.risk_engine import (  # noqa: E402
    REGISTRY_PATH,
    RiskEntry,
    build_risks,
    load_registry,
    ranked_risks,
    risks_by_subsystem,
)

REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-risk-register.txt"
SCREENING_CAVEAT = (
    "This is a screening-level risk register, not formal FMEA, validation evidence, "
    "supplier approval, or production readiness evidence."
)


def _fmt_score(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.1f}"


def _render_list(items: tuple[str, ...], indent: str = "      ") -> list[str]:
    return [f"{indent}- {item}" for item in items]


def _score_line(risk: RiskEntry) -> str:
    return (
        f"score={_fmt_score(risk.total_risk_score)} "
        f"(likelihood {risk.likelihood_score} x impact {risk.impact_score} "
        f"+ maturity penalty {_fmt_score(risk.maturity_penalty)})"
    )


def render_report(risks: tuple[RiskEntry, ...] | None = None) -> str:
    """Render the engineering risk register report."""
    risk_rows = risks if risks is not None else build_risks()
    ranked = ranked_risks(risk_rows)
    severity_counts = Counter(risk.severity.value for risk in risk_rows)
    status_counts = Counter(risk.status for risk in risk_rows)
    blocked_or_critical = [
        risk for risk in ranked if risk.status == "blocked" or risk.severity.value == "CRITICAL"
    ]

    lines = [
        "Slate Pocket Engineering Risk Register v1",
        "==========================================",
        "",
        "Executive risk summary:",
        "  scope: Slate Pocket v1 and v1R",
        "  purpose: rank fragile assumptions, physical gate failures, recovery tradeoffs, and thermal consequence findings as engineering risks",
        f"  total risks: {len(risk_rows)}",
        (
            "  severity counts: "
            f"CRITICAL={severity_counts['CRITICAL']}, HIGH={severity_counts['HIGH']}, "
            f"MEDIUM={severity_counts['MEDIUM']}, LOW={severity_counts['LOW']}"
        ),
        (
            "  status counts: "
            f"blocked={status_counts['blocked']}, open={status_counts['open']}, "
            f"monitoring={status_counts['monitoring']}, mitigated={status_counts['mitigated']}, "
            f"accepted={status_counts['accepted']}"
        ),
        f"  highest ranked risk: {ranked[0].risk_id} - {ranked[0].severity.value} - {_score_line(ranked[0])}",
        f"  register source: {REGISTRY_PATH.relative_to(REPO_ROOT)}",
        "",
        "Caveat:",
        f"  {SCREENING_CAVEAT}",
        "",
        "Scoring method:",
        "  low=1, medium=2, high=3, critical=4",
        "  maturity penalty: concept=+2, screening=+1, first_order=+0.5, calibrated=+0, validated=-1",
        "  total score = likelihood_score * impact_score + maturity_penalty",
        "  severity: CRITICAL >= 13, HIGH >= 8, MEDIUM >= 4, LOW < 4",
        "",
        "Top 10 risks:",
    ]
    for index, risk in enumerate(ranked[:10], start=1):
        lines.extend(
            [
                f"  {index}. {risk.risk_id} - {risk.severity.value} - {_score_line(risk)}",
                f"     title: {risk.title}",
                f"     subsystem: {risk.subsystem}",
                f"     status: {risk.status}",
                f"     profile_scope: {risk.profile_scope}",
            ]
        )

    lines.extend(["", "Blocked/critical risks:"])
    for risk in blocked_or_critical:
        lines.extend(
            [
                f"  - {risk.risk_id} - {risk.severity.value} - {risk.status} - {_score_line(risk)}",
                f"    why it matters: {risk.notes}",
            ]
        )

    lines.extend(["", "All risk entries grouped by subsystem:"])
    for subsystem, subsystem_risks in risks_by_subsystem(risk_rows).items():
        lines.append(f"  {subsystem}:")
        for risk in subsystem_risks:
            lines.extend(
                [
                    f"    - {risk.risk_id}: {risk.title}",
                    f"      severity: {risk.severity.value}",
                    f"      status: {risk.status}",
                    f"      profile_scope: {risk.profile_scope}",
                    f"      likelihood: {risk.likelihood} ({risk.likelihood_score})",
                    f"      impact: {risk.impact} ({risk.impact_score})",
                    f"      maturity: {risk.maturity} (penalty {_fmt_score(risk.maturity_penalty)})",
                    f"      total risk score: {_fmt_score(risk.total_risk_score)}",
                    "      affected reports:",
                ]
            )
            lines.extend(_render_list(risk.affected_reports))
            lines.append("      related assumptions:")
            lines.extend(_render_list(risk.related_assumptions))
            lines.extend(["      notes:", f"        {risk.notes}"])

    lines.extend(["", "Evidence required:"])
    for risk in ranked:
        lines.append(f"  - {risk.risk_id}:")
        lines.extend(_render_list(risk.evidence_required, indent="    "))

    lines.extend(["", "Mitigation summary:"])
    for risk in ranked:
        lines.append(f"  - {risk.risk_id}:")
        lines.extend(_render_list(risk.mitigation, indent="    "))

    lines.extend(["", "Register caveat:", f"  {SCREENING_CAVEAT}", ""])
    return "\n".join(lines)


def build_report() -> str:
    """Build the rendered risk register report."""
    registry = load_registry()
    return render_report(build_risks(registry))


def main() -> int:
    report = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
