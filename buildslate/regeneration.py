"""Hash-based impact analysis and controlled deterministic regeneration."""

from __future__ import annotations

import fnmatch
import hashlib
import subprocess
from pathlib import Path
from typing import Any, Iterable

from .io import dump_yaml, load_yaml


TEXT_SUFFIXES = {
    ".cfg",
    ".csv",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}


def deterministic_file_digest(path: Path) -> str:
    """Hash text with canonical LF endings and preserve binary bytes exactly."""
    content = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"declared text input is not UTF-8: {path}") from exc
        content = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(content).hexdigest()


class RegenerationEngine:
    def __init__(self, repo_root: Path, manifest_path: str = "engineering/program/regeneration.yaml") -> None:
        self.repo_root = repo_root.resolve()
        self.manifest_path = self._repo_path(manifest_path)
        self.manifest = load_yaml(self.manifest_path)
        self.nodes: dict[str, dict[str, Any]] = self.manifest.get("nodes", {})
        self._validate()

    def _repo_path(self, value: str | Path) -> Path:
        path = Path(value)
        candidate = path.resolve() if path.is_absolute() else (self.repo_root / path).resolve()
        try:
            candidate.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError(f"path escapes repository: {value}") from exc
        return candidate

    def _validate(self) -> None:
        if self.manifest.get("metadata", {}).get("schema_version") != 1:
            raise ValueError("regeneration manifest requires schema_version 1")
        if not self.nodes:
            raise ValueError("regeneration manifest requires nodes")
        for node_id, node in self.nodes.items():
            if not isinstance(node, dict):
                raise ValueError(f"regeneration node {node_id} must be a mapping")
            for field in ("depends_on", "inputs", "outputs", "command"):
                if not isinstance(node.get(field), list):
                    raise ValueError(f"regeneration node {node_id} requires list {field}")
            unknown = set(node["depends_on"]) - set(self.nodes)
            if unknown:
                raise ValueError(f"regeneration node {node_id} has unknown dependencies: {sorted(unknown)}")
            if not node["outputs"] or not node["command"]:
                raise ValueError(f"regeneration node {node_id} requires outputs and command")
            for output in node["outputs"]:
                self._repo_path(output)
        self.topological_order()
        self._repo_path(self.manifest["state_file"])

    def topological_order(self) -> tuple[str, ...]:
        order: list[str] = []
        temporary: set[str] = set()
        permanent: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in permanent:
                return
            if node_id in temporary:
                raise ValueError(f"regeneration dependency cycle at {node_id}")
            temporary.add(node_id)
            for dependency in self.nodes[node_id]["depends_on"]:
                visit(dependency)
            temporary.remove(node_id)
            permanent.add(node_id)
            order.append(node_id)

        for node_id in self.nodes:
            visit(node_id)
        return tuple(order)

    def _relative_files(self, pattern: str) -> tuple[str, ...]:
        if any(character in pattern for character in "*?["):
            paths = self.repo_root.glob(pattern)
        else:
            path = self._repo_path(pattern)
            paths = (path,) if path.exists() else ()
        return tuple(
            sorted(
                path.resolve().relative_to(self.repo_root).as_posix()
                for path in paths
                if path.is_file()
            )
        )

    def _digest(self, relative_path: str) -> str:
        return deterministic_file_digest(self._repo_path(relative_path))

    def _digests(self, patterns: Iterable[str]) -> dict[str, str]:
        files = {path for pattern in patterns for path in self._relative_files(pattern)}
        return {path: self._digest(path) for path in sorted(files)}

    def build_state(self) -> dict[str, Any]:
        return {
            "state_version": 2,
            "hash_policy": "utf8_text_lf_binary_exact_sha256_v1",
            "manifest_sha256": deterministic_file_digest(self.manifest_path),
            "nodes": {
                node_id: {
                    "inputs": self._digests(self.nodes[node_id]["inputs"]),
                    "outputs": self._digests(self.nodes[node_id]["outputs"]),
                }
                for node_id in self.topological_order()
            },
            "caveat": "Text hashes canonicalize line endings for cross-platform staleness; binary hashes preserve exact bytes. Neither verifies engineering evidence or physical results.",
        }

    def load_state(self) -> dict[str, Any] | None:
        path = self._repo_path(self.manifest["state_file"])
        return load_yaml(path) if path.exists() else None

    def stale_nodes(self) -> tuple[str, ...]:
        saved = self.load_state()
        current = self.build_state()
        if (
            not saved
            or saved.get("state_version") != current["state_version"]
            or saved.get("hash_policy") != current["hash_policy"]
            or saved.get("manifest_sha256") != current["manifest_sha256"]
        ):
            return self.topological_order()
        stale: set[str] = set()
        for node_id in self.topological_order():
            saved_node = saved.get("nodes", {}).get(node_id)
            current_node = current["nodes"][node_id]
            if saved_node != current_node or not current_node["outputs"]:
                stale.add(node_id)
            if any(dependency in stale for dependency in self.nodes[node_id]["depends_on"]):
                stale.add(node_id)
        return tuple(node_id for node_id in self.topological_order() if node_id in stale)

    def impacted_nodes(self, changed_paths: Iterable[str]) -> tuple[str, ...]:
        normalized = [Path(path).as_posix().lstrip("./") for path in changed_paths]
        impacted: set[str] = set()
        for node_id, node in self.nodes.items():
            if any(fnmatch.fnmatch(path, pattern) for path in normalized for pattern in node["inputs"]):
                impacted.add(node_id)
        changed = True
        while changed:
            changed = False
            for node_id, node in self.nodes.items():
                if node_id not in impacted and any(dependency in impacted for dependency in node["depends_on"]):
                    impacted.add(node_id)
                    changed = True
        return tuple(node_id for node_id in self.topological_order() if node_id in impacted)

    def regenerate(self, node_ids: Iterable[str], dry_run: bool = False) -> tuple[str, ...]:
        selected = set(node_ids)
        ordered = tuple(node_id for node_id in self.topological_order() if node_id in selected)
        if dry_run:
            return ordered
        for node_id in ordered:
            node = self.nodes[node_id]
            result = subprocess.run(
                [str(part) for part in node["command"]],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip()
                raise ValueError(f"generator {node_id} failed with exit {result.returncode}: {detail}")
            missing = [output for output in node["outputs"] if not self._repo_path(output).is_file()]
            if missing:
                raise ValueError(f"generator {node_id} did not create outputs: {missing}")
        state_path = self._repo_path(self.manifest["state_file"])
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(dump_yaml(self.build_state()), encoding="utf-8")
        return ordered

