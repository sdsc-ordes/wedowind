"""Typed catalog metadata (Group, Artefact, Version) for compare/pull vs OEP Databus."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from databus_manager.objects.logs import DiscrepancyLogEntry
from databus_manager.handle_jsonld import (
    get_graph_node,
    load_json,
    version_id_to_artefact_id,
    version_id_to_group_id,
    write_json,
)


@dataclass
class CatalogVersionRef:
    """One catalog ``version.jsonld`` plus resolved paths and URIs for group and artifact."""

    version_file: Path
    group_file: Path
    artifact_file: Path
    version_id: str
    group_id: str
    artifact_id: str


# --- Group ---


@dataclass(frozen=True)
class GroupMetadata:
    """Values from a catalog ``group-metadata.jsonld`` Group node or SPARQL-backed remote."""

    entity_id: str
    title: str
    abstract: str
    description: str

    FIELDS = ("title", "abstract", "description")

    @classmethod
    def from_graph_node(cls, node: dict[str, Any]) -> GroupMetadata:
        return cls(
            entity_id=str(node.get("@id", "")),
            title=str(node.get("title", "")),
            abstract=str(node.get("abstract", "")),
            description=str(node.get("description", "")),
        )

    @classmethod
    def from_jsonld_file(cls, path: Path) -> GroupMetadata:
        doc = load_json(path)
        return cls.from_graph_node(get_graph_node(doc, "Group"))

    @classmethod
    def from_remote_dict(cls, entity_id: str, row: dict[str, Any]) -> GroupMetadata:
        return cls(
            entity_id=entity_id,
            title=str(row.get("title", "")),
            abstract=str(row.get("abstract", "")),
            description=str(row.get("description", "")),
        )

    def normalized(self) -> dict[str, str]:
        return {k: str(getattr(self, k) or "") for k in self.FIELDS}

    def equals_normalized(self, other: GroupMetadata) -> bool:
        return self.normalized() == other.normalized()

    def discrepancies_vs(
        self,
        remote: GroupMetadata | None,
        *,
        timestamp: str,
    ) -> list[DiscrepancyLogEntry]:
        if remote is None:
            return []
        out: list[DiscrepancyLogEntry] = []
        for field in self.FIELDS:
            lv, rv = getattr(self, field), getattr(remote, field)
            if str(lv or "") == str(rv or ""):
                continue
            out.append(
                DiscrepancyLogEntry(
                    timestamp=timestamp,
                    entity_id=self.entity_id,
                    entity_type="group",
                    metadata_field=field,
                    remote_value=rv,
                    local_value=lv,
                )
            )
        return out

    @staticmethod
    def write_remote_to_file(path: Path, remote: GroupMetadata) -> None:
        doc = load_json(path)
        node = get_graph_node(doc, "Group")
        for field in GroupMetadata.FIELDS:
            val = getattr(remote, field)
            if val not in (None, ""):
                node[field] = val
        write_json(path, doc)


# --- Artefact ---


@dataclass(frozen=True)
class ArtefactMetadata:
    """Values from ``artifact-metadata.jsonld`` Artifact node or SPARQL-backed remote."""

    entity_id: str
    title: str
    abstract: str
    description: str

    FIELDS = ("title", "abstract", "description")

    @classmethod
    def from_graph_node(cls, node: dict[str, Any]) -> ArtefactMetadata:
        return cls(
            entity_id=str(node.get("@id", "")),
            title=str(node.get("title", "")),
            abstract=str(node.get("abstract", "")),
            description=str(node.get("description", "")),
        )

    @classmethod
    def from_jsonld_file(cls, path: Path) -> ArtefactMetadata:
        doc = load_json(path)
        return cls.from_graph_node(get_graph_node(doc, "Artifact"))

    @classmethod
    def from_remote_dict(cls, entity_id: str, row: dict[str, Any]) -> ArtefactMetadata:
        return cls(
            entity_id=entity_id,
            title=str(row.get("title", "")),
            abstract=str(row.get("abstract", "")),
            description=str(row.get("description", "")),
        )

    def normalized(self) -> dict[str, str]:
        return {k: str(getattr(self, k) or "") for k in self.FIELDS}

    def equals_normalized(self, other: ArtefactMetadata) -> bool:
        return self.normalized() == other.normalized()

    def discrepancies_vs(
        self,
        remote: ArtefactMetadata | None,
        *,
        timestamp: str,
    ) -> list[DiscrepancyLogEntry]:
        if remote is None:
            return []
        out: list[DiscrepancyLogEntry] = []
        for field in self.FIELDS:
            lv, rv = getattr(self, field), getattr(remote, field)
            if str(lv or "") == str(rv or ""):
                continue
            out.append(
                DiscrepancyLogEntry(
                    timestamp=timestamp,
                    entity_id=self.entity_id,
                    entity_type="artifact",
                    metadata_field=field,
                    remote_value=rv,
                    local_value=lv,
                )
            )
        return out

    @staticmethod
    def write_remote_to_file(path: Path, remote: ArtefactMetadata) -> None:
        doc = load_json(path)
        node = get_graph_node(doc, "Artifact")
        for field in ArtefactMetadata.FIELDS:
            val = getattr(remote, field)
            if val not in (None, ""):
                node[field] = val
        write_json(path, doc)


# --- Version ---


@dataclass(frozen=True)
class VersionMetadata:
    """Version node for compare (scalar fields + normalized distribution tuples)."""

    entity_id: str
    title: str
    abstract: str
    description: str
    license: str
    distribution: list[dict[str, Any]] | None

    SCALAR_FIELDS = ("title", "abstract", "description", "license")

    @classmethod
    def from_graph_node(cls, node: dict[str, Any]) -> VersionMetadata:
        dist = node.get("distribution")
        if not isinstance(dist, list):
            dist = None
        return cls(
            entity_id=str(node.get("@id", "")),
            title=str(node.get("title", "")),
            abstract=str(node.get("abstract", "")),
            description=str(node.get("description", "")),
            license=str(node.get("license", "")),
            distribution=dist,
        )

    @classmethod
    def from_jsonld_file(cls, path: Path) -> VersionMetadata:
        doc = load_json(path)
        return cls.from_graph_node(get_graph_node(doc, "Version"))

    @classmethod
    def from_remote_dict(cls, entity_id: str, payload: dict[str, Any]) -> VersionMetadata:
        dist = payload.get("distribution")
        if not isinstance(dist, list):
            dist = None
        return cls(
            entity_id=entity_id,
            title=str(payload.get("title", "")),
            abstract=str(payload.get("abstract", "")),
            description=str(payload.get("description", "")),
            license=str(payload.get("license", "")),
            distribution=dist,
        )

    def normalized(self) -> dict[str, Any]:
        parts = self.distribution or []
        norm_parts = sorted(
            [
                (
                    str(p.get("downloadURL", "")),
                    str(p.get("formatExtension", "")),
                    str(p.get("compression", "")),
                )
                for p in parts
                if isinstance(p, dict)
            ]
        )
        return {
            "title": str(self.title or ""),
            "abstract": str(self.abstract or ""),
            "description": str(self.description or ""),
            "license": str(self.license or ""),
            "distribution": norm_parts,
        }

    def equals_normalized(self, other: VersionMetadata) -> bool:
        return self.normalized() == other.normalized()

    def discrepancies_vs(
        self,
        remote: VersionMetadata | None,
        *,
        timestamp: str,
    ) -> list[DiscrepancyLogEntry]:
        if remote is None:
            return []
        out: list[DiscrepancyLogEntry] = []
        for field in self.SCALAR_FIELDS:
            lv, rv = getattr(self, field), getattr(remote, field)
            if str(lv or "") == str(rv or ""):
                continue
            out.append(
                DiscrepancyLogEntry(
                    timestamp=timestamp,
                    entity_id=self.entity_id,
                    entity_type="version",
                    metadata_field=field,
                    remote_value=rv,
                    local_value=lv,
                )
            )
        if self.normalized()["distribution"] != remote.normalized()["distribution"]:
            out.append(
                DiscrepancyLogEntry(
                    timestamp=timestamp,
                    entity_id=self.entity_id,
                    entity_type="version",
                    metadata_field="distribution",
                    remote_value=remote.distribution,
                    local_value=self.distribution,
                )
            )
        return out

    @staticmethod
    def write_remote_to_file(path: Path, remote: VersionMetadata) -> None:
        doc = load_json(path)
        node = get_graph_node(doc, "Version")
        for field in VersionMetadata.SCALAR_FIELDS:
            val = getattr(remote, field)
            if val not in (None, ""):
                node[field] = val
        if remote.distribution:
            node["distribution"] = remote.distribution
        write_json(path, doc)
