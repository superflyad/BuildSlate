"""Human-readable evidence, gate, contradiction, staleness, and action dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .configuration import ConfigurationResolver
from .contracts import IntegrationContractRepository
from .evt0 import EVT0CampaignRepository
from .io import dump_yaml, load_yaml
from .manufacturing import ManufacturingAnalyticsRepository
from .program import ProgramRepository
from .regeneration import RegenerationEngine
from .suppliers import SupplierResponseRepository


class ProgramDashboard:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def build(self, assume_upstream_current: bool = False) -> dict[str, Any]:
        evidence = load_yaml(self.repo_root / "engineering/evidence/evidence_registry.yaml")["packages"]
        blockers = load_yaml(self.repo_root / "engineering/evidence/external_blocker_registry.yaml")["blockers"]
        configuration = ConfigurationResolver(self.repo_root)
        resolution = configuration.resolve()
        supplier = SupplierResponseRepository(self.repo_root).build_review_queue()
        contracts = IntegrationContractRepository(self.repo_root).evaluate()
        evt0 = EVT0CampaignRepository(self.repo_root).build_campaign_report()
        manufacturing = ManufacturingAnalyticsRepository(self.repo_root).build_report()
        snapshot = ProgramRepository(self.repo_root).build_snapshot()
        stale = [] if assume_upstream_current else [
            node for node in RegenerationEngine(self.repo_root).stale_nodes()
            if node not in {"dashboard", "program_snapshot"}
        ]

        verified = [
            {"id": package_id, "title": package["title"], "status": package["status"]}
            for package_id, package in evidence.items() if package["status"] == "verified"
        ]
        available = [
            {"id": package_id, "title": package["title"], "status": package["status"], "phase": package["phase"]}
            for package_id, package in evidence.items() if package["status"] == "available"
        ]
        modeled = [
            {
                "id": package_id,
                "title": package["title"],
                "evidence_status": package["status"],
                "model_status": "planning_artifacts_present_not_verified",
            }
            for package_id, package in evidence.items() if package["phase"] == 2
        ]
        rejected = [
            {"id": entry_id, "value": entry["value"], "unit": entry.get("unit"), "notes": entry.get("notes")}
            for entry_id, entry in configuration.registry["entries"].items() if entry["state"] == "rejected_option"
        ]
        contradictions: list[dict[str, Any]] = []
        contradictions.extend({"source": "configuration", **item} for item in resolution["violations"])
        contradictions.extend({"source": "integration_contract", **item} for item in contracts["contradictions"])
        for item in supplier["items"]:
            for contradiction in item.get("review", {}).get("contradictions", []):
                contradictions.append({"source": "supplier_response", "receipt": item["receipt"], **contradiction})
            for error in item.get("integrity_errors", []):
                contradictions.append({"source": "supplier_integrity", "receipt": item["receipt"], "issue": error})
        for run in evt0["runs"]:
            if run["objective_disposition"] in {"REJECTED_INVALID_EVIDENCE", "ABORTED_OR_HARD_STOP"}:
                contradictions.append({"source": "evt0", "run_id": run.get("run_id"), "issue": run["objective_disposition"]})
        for campaign in manufacturing["campaigns"]:
            if campaign["PILOT_GATE"] in {"REJECTED_INVALID_EVIDENCE", "STOP_QUARANTINE_AND_REVIEW"}:
                contradictions.append({"source": "manufacturing", "campaign_id": campaign.get("campaign_id"), "issue": campaign["PILOT_GATE"]})

        external = [
            {
                "id": blocker_id,
                "category": blocker["category"],
                "missing_evidence": blocker["missing_evidence"],
                "exact_next_action": blocker["exact_request"],
                "authorization_required": blocker["authorization_required"],
                "fallback": blocker["fallback"],
            }
            for blocker_id, blocker in blockers.items()
        ]
        gates = [
            {"id": entity.entity_id.removeprefix("gate:"), "status": entity.status, "source": entity.source_path}
            for entity in snapshot.entities if entity.kind == "gate"
        ]
        if contradictions:
            dashboard_gate = "LOCAL_CONTRADICTIONS_REQUIRE_REVIEW"
        elif stale:
            dashboard_gate = "LOCAL_OUTPUTS_STALE"
        else:
            dashboard_gate = "LOCAL_SYSTEM_CURRENT_EXTERNALLY_BLOCKED"
        return {
            "DASHBOARD_GATE": dashboard_gate,
            "program_id": snapshot.program_id,
            "summary": {
                "verified": len(verified),
                "available_not_verified": len(available),
                "modeled_not_verified": len(modeled),
                "rejected_options": len(rejected),
                "stale_nodes": len(stale),
                "contradictions": len(contradictions),
                "external_blockers": len(external),
            },
            "gates": gates,
            "verified": verified,
            "available_not_verified": available,
            "modeled_not_verified": modeled,
            "rejected_options": rejected,
            "stale_nodes": stale,
            "contradictions": contradictions,
            "externally_blocked": external,
            "exact_next_actions": [
                {"blocker": item["id"], "action": item["exact_next_action"], "authorization_required": item["authorization_required"]}
                for item in external
            ],
            "caveat": "Artifact presence, current hashes, and consistent interfaces do not convert modeled or available evidence into verified evidence.",
        }

    def render_markdown(self, dashboard: dict[str, Any]) -> str:
        lines = [
            "# Slate Pocket v1R Program Dashboard",
            "",
            f"**Dashboard gate:** `{dashboard['DASHBOARD_GATE']}`",
            "",
            "This is a generated evidence and action view. It does not approve suppliers, components, builds, tests, certification, or production.",
            "",
            "## Evidence summary",
            "",
            "| Class | Count | Meaning |",
            "|---|---:|---|",
            f"| Verified | {dashboard['summary']['verified']} | Acceptance criteria met in the evidence registry |",
            f"| Available, not verified | {dashboard['summary']['available_not_verified']} | Reviewable evidence exists but is incomplete or unverified |",
            f"| Modeled, not verified | {dashboard['summary']['modeled_not_verified']} | Phase 2 planning models exist without verified inputs/results |",
            f"| Rejected options | {dashboard['summary']['rejected_options']} | Explicitly prohibited or rejected configurations retained for traceability |",
            f"| Stale nodes | {dashboard['summary']['stale_nodes']} | Generated outputs whose recorded hashes do not match |",
            f"| Contradictions | {dashboard['summary']['contradictions']} | Authority, integrity, supplier, campaign, or cross-domain conflicts |",
            f"| External blockers | {dashboard['summary']['external_blockers']} | Work requiring authorization or external evidence |",
            "",
            "## Gate status",
            "",
        ]
        lines.extend(f"- `{item['id']}`: `{item['status']}` — `{item['source']}`" for item in dashboard["gates"])
        lines.extend(["", "## Rejected options", ""])
        lines.extend(f"- `{item['id']}`: {item['value']} {item.get('unit') or ''} — {item.get('notes') or 'retained as rejected'}" for item in dashboard["rejected_options"])
        lines.extend(["", "## Stale or contradictory local state", ""])
        if not dashboard["stale_nodes"] and not dashboard["contradictions"]:
            lines.append("- None. All tracked generated nodes are current and no contradiction queue is open.")
        else:
            lines.extend(f"- Stale generator: `{node}`" for node in dashboard["stale_nodes"])
            lines.extend(f"- Contradiction: `{item.get('source')}` — `{item.get('issue', item.get('rule_id', 'review required'))}`" for item in dashboard["contradictions"])
        lines.extend(["", "## Exact externally blocked next actions", ""])
        for index, item in enumerate(dashboard["externally_blocked"], start=1):
            lines.extend(
                [
                    f"{index}. **{item['id']}** (`{item['category']}`)",
                    f"   - Missing: {item['missing_evidence']}",
                    f"   - Action: {item['exact_next_action']}",
                    f"   - Authorization: `{item['authorization_required']}`",
                    f"   - Active fallback: {item['fallback']}",
                ]
            )
        lines.extend(["", f"> {dashboard['caveat']}", ""])
        return "\n".join(lines)

    def generate(self, assume_upstream_current: bool = False) -> tuple[Path, Path]:
        dashboard = self.build(assume_upstream_current=assume_upstream_current)
        yaml_path = self.repo_root / "reports/program/dashboard.yaml"
        markdown_path = self.repo_root / "reports/program/dashboard.md"
        yaml_path.write_text(dump_yaml(dashboard), encoding="utf-8")
        markdown_path.write_text(self.render_markdown(dashboard), encoding="utf-8")
        return yaml_path, markdown_path

