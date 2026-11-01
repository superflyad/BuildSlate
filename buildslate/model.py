"""Immutable program-graph data structures."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProgramEntity:
    """One traceable engineering entity."""

    entity_id: str
    kind: str
    title: str
    status: str
    source_path: str
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProgramRelation:
    """A typed edge between two program entities."""

    source_id: str
    relationship: str
    target_id: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ProgramSnapshot:
    """Deterministic point-in-time program graph."""

    schema_version: int
    program_id: str
    title: str
    entities: tuple[ProgramEntity, ...]
    relations: tuple[ProgramRelation, ...]
    summary: dict[str, Any]
    caveat: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "program_id": self.program_id,
            "title": self.title,
            "summary": self.summary,
            "entities": [entity.to_dict() for entity in self.entities],
            "relations": [relation.to_dict() for relation in self.relations],
            "caveat": self.caveat,
        }
