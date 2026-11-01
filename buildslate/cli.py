"""BuildSlate command-line interface."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

from .io import dump_json, dump_yaml
from .program import DEFAULT_REPO_ROOT, ProgramRepository, compare_yaml


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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
