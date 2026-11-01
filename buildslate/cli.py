"""BuildSlate command-line interface."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

from .configuration import ConfigurationResolver
from .contracts import IntegrationContractRepository
from .evt0 import EVT0CampaignRepository
from .io import dump_json, dump_yaml
from .manufacturing import ManufacturingAnalyticsRepository
from .program import DEFAULT_REPO_ROOT, ProgramRepository, compare_yaml
from .regeneration import RegenerationEngine
from .suppliers import SupplierResponseRepository


def _emit(data: Any, output_format: str) -> None:
    if output_format == "json":
        print(dump_json(data))
    elif output_format == "yaml":
        print(dump_yaml(data), end="")
    else:
        raise ValueError(f"unsupported structured format: {output_format}")


def _repository(args: argparse.Namespace) -> ProgramRepository:
    return ProgramRepository(Path(args.repo_root))


def command_validate(args: argparse.Namespace) -> int:
    repository = _repository(args)
    snapshot = repository.build_snapshot()
    print(f"PASS: program manifest and graph ({snapshot.summary['entity_count']} entities, {snapshot.summary['relation_count']} relations)")
    if args.all:
        result = subprocess.run([sys.executable, "validation/run_all.py"], cwd=repository.repo_root, check=False)
        return result.returncode
    return 0


def command_status(args: argparse.Namespace) -> int:
    snapshot = _repository(args).build_snapshot()
    gates = [entity.to_dict() for entity in snapshot.entities if entity.kind == "gate"]
    payload = {"program_id": snapshot.program_id, "title": snapshot.title, "summary": snapshot.summary, "gates": gates, "caveat": snapshot.caveat}
    if args.format in {"json", "yaml"}:
        _emit(payload, args.format)
        return 0
    print(snapshot.title)
    print(f"entities: {snapshot.summary['entity_count']}")
    print(f"relations: {snapshot.summary['relation_count']}")
    print("evidence: " + ", ".join(f"{key}={value}" for key, value in snapshot.summary["evidence_status_counts"].items()))
    print("gates:")
    for gate in gates:
        print(f"  {gate['entity_id']}: {gate['status']}")
    print(f"caveat: {snapshot.caveat}")
    return 0


def command_blockers(args: argparse.Namespace) -> int:
    blockers = _repository(args).blockers()
    if args.id:
        wanted = args.id if args.id.startswith("blocker:") else f"blocker:{args.id}"
        blockers = tuple(blocker for blocker in blockers if blocker.entity_id == wanted)
        if not blockers:
            print(f"ERROR: unknown blocker: {args.id}", file=sys.stderr)
            return 2
    payload = [blocker.to_dict() for blocker in blockers]
    if args.format in {"json", "yaml"}:
        _emit(payload, args.format)
        return 0
    for blocker in blockers:
        print(f"{blocker.entity_id} [{blocker.attributes['category']}]")
        print(f"  missing: {blocker.attributes['missing_evidence']}")
        print(f"  request: {blocker.attributes['exact_request']}")
        print(f"  fallback: {blocker.attributes['fallback']}")
        print(f"  authorization: {blocker.attributes['authorization_required']}")
    return 0


def command_compare(args: argparse.Namespace) -> int:
    repository = _repository(args)
    left = Path(args.left)
    right = Path(args.right)
    if not left.is_absolute():
        left = repository.repo_root / left
    if not right.is_absolute():
        right = repository.repo_root / right
    differences = compare_yaml(left, right)
    payload = {"left": str(left.relative_to(repository.repo_root)), "right": str(right.relative_to(repository.repo_root)), "difference_count": len(differences), "differences": differences}
    if args.format in {"json", "yaml"}:
        _emit(payload, args.format)
        return 0
    print(f"compare: {payload['left']} -> {payload['right']}")
    print(f"differences: {len(differences)}")
    for difference in differences:
        print(f"  {difference['path']}: {difference['left']!r} -> {difference['right']!r}")
    return 0


def command_generate(args: argparse.Namespace) -> int:
    repository = _repository(args)
    destination = repository.generate_snapshot(Path(args.output) if args.output else None)
    print(f"Wrote {destination.relative_to(repository.repo_root)}")
    return 0


def _supplier_repository(args: argparse.Namespace) -> SupplierResponseRepository:
    return SupplierResponseRepository(Path(args.repo_root))


def command_suppliers_validate(args: argparse.Namespace) -> int:
    review = _supplier_repository(args).validate_response(Path(args.response), args.domain)
    if args.format in {"json", "yaml"}:
        _emit(review.to_dict(), args.format)
    else:
        print(f"domain: {review.domain}")
        print(f"disposition: {review.disposition}")
        print(f"completeness: {review.completeness_percent:.1f}%")
        print(f"schema_errors: {len(review.schema_errors)}")
        print(f"provenance_issues: {len(review.provenance_issues)}")
        print(f"contradictions: {len(review.contradictions)}")
    return 2 if review.schema_errors else 0


def command_suppliers_ingest(args: argparse.Namespace) -> int:
    receipt, review = _supplier_repository(args).ingest(
        Path(args.response), args.domain, args.received_at, args.received_by
    )
    print(f"Wrote {receipt.relative_to(Path(args.repo_root).resolve())}")
    print(f"disposition: {review.disposition}")
    print("evidence_effect: none")
    return 0


def command_suppliers_queue(args: argparse.Namespace) -> int:
    repository = _supplier_repository(args)
    queue = repository.build_review_queue()
    if args.generate:
        destination = repository.generate_review_queue()
        print(f"Wrote {destination.relative_to(repository.repo_root)}")
    if args.format in {"json", "yaml"}:
        _emit(queue, args.format)
    elif not args.generate:
        print(f"gate: {queue['SUPPLIER_RESPONSE_GATE']}")
        print(f"receipts: {queue['summary']['receipt_count']}")
        for item in queue["items"]:
            print(f"  {item['receipt']}: {item['disposition']}")
    return 0


def command_configuration_validate(args: argparse.Namespace) -> int:
    resolution = ConfigurationResolver(Path(args.repo_root)).resolve()
    if args.format in {"json", "yaml"}:
        _emit(resolution, args.format)
    else:
        print(f"gate: {resolution['CONFIGURATION_GATE']}")
        print(f"bindings: {len(resolution['resolved_bindings'])}")
        print(f"violations: {len(resolution['violations'])}")
        print(f"unresolved_decisions: {len(resolution['unresolved_decisions'])}")
    return 2 if resolution["violations"] else 0


def command_configuration_generate(args: argparse.Namespace) -> int:
    resolver = ConfigurationResolver(Path(args.repo_root))
    destination = resolver.generate()
    resolution = resolver.resolve()
    print(f"Wrote {destination.relative_to(resolver.repo_root)}")
    print(f"gate: {resolution['CONFIGURATION_GATE']}")
    return 2 if resolution["violations"] else 0


def command_impact(args: argparse.Namespace) -> int:
    engine = RegenerationEngine(Path(args.repo_root))
    impacted = engine.impacted_nodes(args.changed)
    payload = {"changed": args.changed, "impacted_count": len(impacted), "impacted_nodes": list(impacted)}
    if args.format in {"json", "yaml"}:
        _emit(payload, args.format)
    else:
        print(f"impacted: {len(impacted)}")
        for node_id in impacted:
            print(f"  {node_id}")
    return 0


def command_stale(args: argparse.Namespace) -> int:
    engine = RegenerationEngine(Path(args.repo_root))
    stale = engine.stale_nodes()
    payload = {"stale_count": len(stale), "stale_nodes": list(stale)}
    if args.format in {"json", "yaml"}:
        _emit(payload, args.format)
    else:
        print(f"stale: {len(stale)}")
        for node_id in stale:
            print(f"  {node_id}")
    return 1 if stale else 0


def command_regenerate(args: argparse.Namespace) -> int:
    engine = RegenerationEngine(Path(args.repo_root))
    nodes = engine.impacted_nodes(args.changed) if args.changed else engine.stale_nodes()
    executed = engine.regenerate(nodes, dry_run=args.dry_run)
    verb = "Would regenerate" if args.dry_run else "Regenerated"
    print(f"{verb} {len(executed)} node(s)")
    for node_id in executed:
        print(f"  {node_id}")
    return 0


def command_contracts_validate(args: argparse.Namespace) -> int:
    result = IntegrationContractRepository(Path(args.repo_root)).evaluate()
    if args.format in {"json", "yaml"}:
        _emit(result, args.format)
    else:
        print(f"gate: {result['INTEGRATION_CONTRACT_GATE']}")
        print(f"domains: {len(result['domain_statuses'])}")
        print(f"checks: {result['check_count']}")
        print(f"contradictions: {result['contradiction_count']}")
    return 2 if result["contradictions"] else 0


def command_contracts_generate(args: argparse.Namespace) -> int:
    repository = IntegrationContractRepository(Path(args.repo_root))
    destination = repository.generate()
    result = repository.evaluate()
    print(f"Wrote {destination.relative_to(repository.repo_root)}")
    print(f"gate: {result['INTEGRATION_CONTRACT_GATE']}")
    return 2 if result["contradictions"] else 0


def command_evt0_validate(args: argparse.Namespace) -> int:
    review = EVT0CampaignRepository(Path(args.repo_root)).review_bundle(Path(args.bundle))
    if args.format in {"json", "yaml"}:
        _emit(review, args.format)
    else:
        print(f"test_id: {review.get('test_id')}")
        print(f"disposition: {review['objective_disposition']}")
        print(f"integrity_errors: {len(review['integrity_errors'])}")
        print(f"calculated_metrics: {len(review.get('calculated_metrics', {}))}")
    return 2 if review["integrity_errors"] else 0


def command_evt0_ingest(args: argparse.Namespace) -> int:
    repository = EVT0CampaignRepository(Path(args.repo_root))
    receipt, review = repository.ingest(Path(args.bundle), args.received_at, args.received_by)
    print(f"Wrote {receipt.relative_to(repository.repo_root)}")
    print(f"objective_disposition: {review['objective_disposition']}")
    print("evidence_effect: review_queue_only")
    return 0


def command_evt0_report(args: argparse.Namespace) -> int:
    repository = EVT0CampaignRepository(Path(args.repo_root))
    report = repository.build_campaign_report()
    if args.generate:
        destination = repository.generate_campaign_report()
        print(f"Wrote {destination.relative_to(repository.repo_root)}")
    if args.format in {"json", "yaml"}:
        _emit(report, args.format)
    elif not args.generate:
        print(f"gate: {report['EVT0_CAMPAIGN_GATE']}")
        print(f"runs: {report['summary']['ingested_run_count']}")
        print(f"passing_required_tests: {report['summary']['passing_required_test_count']}/{report['summary']['required_test_count']}")
    return 0


def command_manufacturing_validate(args: argparse.Namespace) -> int:
    review = ManufacturingAnalyticsRepository(Path(args.repo_root)).review_bundle(Path(args.bundle))
    if args.format in {"json", "yaml"}:
        _emit(review, args.format)
    else:
        print(f"campaign_id: {review.get('campaign_id')}")
        print(f"gate: {review['PILOT_GATE']}")
        print(f"integrity_errors: {len(review['integrity_errors'])}")
        print(f"denominator: {review.get('denominator', {}).get('input_units')}")
    return 2 if review["integrity_errors"] else 0


def command_manufacturing_ingest(args: argparse.Namespace) -> int:
    repository = ManufacturingAnalyticsRepository(Path(args.repo_root))
    receipt, review = repository.ingest(Path(args.bundle), args.received_at, args.received_by)
    print(f"Wrote {receipt.relative_to(repository.repo_root)}")
    print(f"pilot_gate: {review['PILOT_GATE']}")
    print("evidence_effect: quality_review_only")
    return 0


def command_manufacturing_report(args: argparse.Namespace) -> int:
    repository = ManufacturingAnalyticsRepository(Path(args.repo_root))
    report = repository.build_report()
    if args.generate:
        destination = repository.generate_report()
        print(f"Wrote {destination.relative_to(repository.repo_root)}")
    if args.format in {"json", "yaml"}:
        _emit(report, args.format)
    elif not args.generate:
        print(f"gate: {report['MANUFACTURING_ANALYTICS_GATE']}")
        print(f"campaigns: {report['campaign_count']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="buildslate", description="BuildSlate engineering execution CLI")
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT), help="BuildSlate repository root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate the unified program graph")
    validate_parser.add_argument("--all", action="store_true", help="also run validation/run_all.py")
    validate_parser.set_defaults(handler=command_validate)

    status_parser = subparsers.add_parser("status", help="show readiness and gate status")
    status_parser.add_argument("--format", choices=("text", "json", "yaml"), default="text")
    status_parser.set_defaults(handler=command_status)

    blocker_parser = subparsers.add_parser("blockers", help="list or explain external blockers")
    blocker_parser.add_argument("--id", help="one blocker id, with or without blocker: prefix")
    blocker_parser.add_argument("--format", choices=("text", "json", "yaml"), default="text")
    blocker_parser.set_defaults(handler=command_blockers)

    compare_parser = subparsers.add_parser("compare", help="compare two YAML configurations")
    compare_parser.add_argument("--left", required=True)
    compare_parser.add_argument("--right", required=True)
    compare_parser.add_argument("--format", choices=("text", "json", "yaml"), default="text")
    compare_parser.set_defaults(handler=command_compare)

    generate_parser = subparsers.add_parser("generate", help="generate the unified program snapshot")
    generate_parser.add_argument("--output", help="override snapshot output path")
    generate_parser.set_defaults(handler=command_generate)

    suppliers_parser = subparsers.add_parser("suppliers", help="validate and ingest supplier responses")
    supplier_commands = suppliers_parser.add_subparsers(dest="supplier_command", required=True)

    supplier_validate = supplier_commands.add_parser("validate", help="validate one response without ingesting it")
    supplier_validate.add_argument("--domain", required=True, choices=("battery", "compute_memory", "display", "storage", "dfm"))
    supplier_validate.add_argument("--response", required=True)
    supplier_validate.add_argument("--format", choices=("text", "json", "yaml"), default="text")
    supplier_validate.set_defaults(handler=command_suppliers_validate)

    supplier_ingest = supplier_commands.add_parser("ingest", help="preserve a schema-valid raw response and receipt")
    supplier_ingest.add_argument("--domain", required=True, choices=("battery", "compute_memory", "display", "storage", "dfm"))
    supplier_ingest.add_argument("--response", required=True)
    supplier_ingest.add_argument("--received-at", required=True, help="explicit ISO-8601 receipt timestamp")
    supplier_ingest.add_argument("--received-by", required=True, help="operator identity recorded in the receipt")
    supplier_ingest.set_defaults(handler=command_suppliers_ingest)

    supplier_queue = supplier_commands.add_parser("queue", help="inspect or regenerate the supplier review queue")
    supplier_queue.add_argument("--generate", action="store_true")
    supplier_queue.add_argument("--format", choices=("text", "json", "yaml"), default="text")
    supplier_queue.set_defaults(handler=command_suppliers_queue)

    configuration_parser = subparsers.add_parser("configuration", help="resolve configuration authority and model bindings")
    configuration_commands = configuration_parser.add_subparsers(dest="configuration_command", required=True)

    configuration_validate = configuration_commands.add_parser("validate", help="validate configuration bindings without writing")
    configuration_validate.add_argument("--format", choices=("text", "json", "yaml"), default="text")
    configuration_validate.set_defaults(handler=command_configuration_validate)

    configuration_generate = configuration_commands.add_parser("generate", help="generate the authoritative resolution report")
    configuration_generate.set_defaults(handler=command_configuration_generate)

    impact_parser = subparsers.add_parser("impact", help="show dependency-aware impact for changed paths")
    impact_parser.add_argument("--changed", nargs="+", required=True)
    impact_parser.add_argument("--format", choices=("text", "json", "yaml"), default="text")
    impact_parser.set_defaults(handler=command_impact)

    stale_parser = subparsers.add_parser("stale", help="show generated nodes with changed inputs or outputs")
    stale_parser.add_argument("--format", choices=("text", "json", "yaml"), default="text")
    stale_parser.set_defaults(handler=command_stale)

    regenerate_parser = subparsers.add_parser("regenerate", help="run controlled generators in dependency order")
    regenerate_selection = regenerate_parser.add_mutually_exclusive_group(required=True)
    regenerate_selection.add_argument("--changed", nargs="+", help="regenerate everything affected by these paths")
    regenerate_selection.add_argument("--stale", action="store_true", help="regenerate all hash-stale nodes")
    regenerate_parser.add_argument("--dry-run", action="store_true")
    regenerate_parser.set_defaults(handler=command_regenerate)

    contracts_parser = subparsers.add_parser("contracts", help="validate Phase 2 integration contracts")
    contract_commands = contracts_parser.add_subparsers(dest="contracts_command", required=True)
    contracts_validate = contract_commands.add_parser("validate", help="run cross-domain consistency checks")
    contracts_validate.add_argument("--format", choices=("text", "json", "yaml"), default="text")
    contracts_validate.set_defaults(handler=command_contracts_validate)
    contracts_generate = contract_commands.add_parser("generate", help="generate the integration-contract report")
    contracts_generate.set_defaults(handler=command_contracts_generate)

    evt0_parser = subparsers.add_parser("evt0", help="validate and ingest EVT0 campaign evidence")
    evt0_commands = evt0_parser.add_subparsers(dest="evt0_command", required=True)
    evt0_validate = evt0_commands.add_parser("validate", help="validate one EVT0 evidence bundle")
    evt0_validate.add_argument("--bundle", required=True)
    evt0_validate.add_argument("--format", choices=("text", "json", "yaml"), default="text")
    evt0_validate.set_defaults(handler=command_evt0_validate)
    evt0_ingest = evt0_commands.add_parser("ingest", help="preserve one valid EVT0 evidence bundle")
    evt0_ingest.add_argument("--bundle", required=True)
    evt0_ingest.add_argument("--received-at", required=True)
    evt0_ingest.add_argument("--received-by", required=True)
    evt0_ingest.set_defaults(handler=command_evt0_ingest)
    evt0_report = evt0_commands.add_parser("report", help="inspect or generate the EVT0 campaign gate")
    evt0_report.add_argument("--generate", action="store_true")
    evt0_report.add_argument("--format", choices=("text", "json", "yaml"), default="text")
    evt0_report.set_defaults(handler=command_evt0_report)

    manufacturing_parser = subparsers.add_parser("manufacturing", help="validate and analyze pilot evidence")
    manufacturing_commands = manufacturing_parser.add_subparsers(dest="manufacturing_command", required=True)
    manufacturing_validate = manufacturing_commands.add_parser("validate", help="validate and analyze one pilot bundle")
    manufacturing_validate.add_argument("--bundle", required=True)
    manufacturing_validate.add_argument("--format", choices=("text", "json", "yaml"), default="text")
    manufacturing_validate.set_defaults(handler=command_manufacturing_validate)
    manufacturing_ingest = manufacturing_commands.add_parser("ingest", help="preserve an authorized pilot bundle")
    manufacturing_ingest.add_argument("--bundle", required=True)
    manufacturing_ingest.add_argument("--received-at", required=True)
    manufacturing_ingest.add_argument("--received-by", required=True)
    manufacturing_ingest.set_defaults(handler=command_manufacturing_ingest)
    manufacturing_report = manufacturing_commands.add_parser("report", help="inspect or generate pilot analytics")
    manufacturing_report.add_argument("--generate", action="store_true")
    manufacturing_report.add_argument("--format", choices=("text", "json", "yaml"), default="text")
    manufacturing_report.set_defaults(handler=command_manufacturing_report)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
