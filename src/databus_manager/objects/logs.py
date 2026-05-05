"""JSON-schema-backed log entries for discrepancy and publishing ledger JSONL files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Literal

import jsonschema
from jsonschema import Draft202012Validator

EntityType = Literal["group", "artefact", "version"]

METADATA_FIELDS_BY_ENTITY: dict[EntityType, frozenset[str]] = {
    "group": frozenset({"title", "abstract", "description"}),
    "artefact": frozenset({"title", "abstract", "description"}),
    "version": frozenset({"title", "abstract", "description", "license", "distribution"}),
}


def schemas_dir() -> Path:
    """Bundled JSON schemas (wheel: ``databus_manager/schemas``) or repo ``src/schemas``."""
    databus_pkg = Path(__file__).resolve().parent.parent
    packaged = databus_pkg / "schemas"
    if packaged.is_dir():
        return packaged
    dev = databus_pkg.parent / "schemas"
    if dev.is_dir():
        return dev
    raise FileNotFoundError(
        "JSON schemas not found; expected databus_manager/schemas or src/schemas."
    )


def _load_schema(name: str) -> dict[str, Any]:
    path = schemas_dir() / name
    return json.loads(path.read_text(encoding="utf-8"))


_discrepancy_validator = Draft202012Validator(_load_schema("discrepancy.schema.json"))
_publishing_validator = Draft202012Validator(_load_schema("publishing.schema.json"))


def validate_discrepancy(instance: dict[str, Any]) -> None:
    _discrepancy_validator.validate(instance)


def validate_publishing(instance: dict[str, Any]) -> None:
    _publishing_validator.validate(instance)


def ensure_metadata_field(entity_type: EntityType, metadata_field: str) -> None:
    allowed = METADATA_FIELDS_BY_ENTITY.get(entity_type)
    if allowed is None or metadata_field not in allowed:
        raise ValueError(f"metadata_field {metadata_field!r} is not valid for entity_type {entity_type!r}")


@dataclass(frozen=True)
class DiscrepancyLogEntry:
    timestamp: str
    entity_id: str
    entity_type: EntityType
    metadata_field: str
    remote_value: Any
    local_value: Any

    def __post_init__(self) -> None:
        ensure_metadata_field(self.entity_type, self.metadata_field)
        validate_discrepancy(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "metadata_field": self.metadata_field,
            "remote_value": self.remote_value,
            "local_value": self.local_value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiscrepancyLogEntry:
        validate_discrepancy(data)
        return cls(
            timestamp=str(data["timestamp"]),
            entity_id=str(data["entity_id"]),
            entity_type=data["entity_type"],  # type: ignore[arg-type]
            metadata_field=str(data["metadata_field"]),
            remote_value=data["remote_value"],
            local_value=data["local_value"],
        )


@dataclass(frozen=True)
class PublishingLedgerEntry:
    timestamp: str
    entity_id: str
    entity_type: EntityType

    def __post_init__(self) -> None:
        validate_publishing(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PublishingLedgerEntry:
        validate_publishing(data)
        return cls(
            timestamp=str(data["timestamp"]),
            entity_id=str(data["entity_id"]),
            entity_type=data["entity_type"],  # type: ignore[arg-type]
        )


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def iter_discrepancy_log(path: Path) -> Iterator[DiscrepancyLogEntry]:
    if not path.is_file():
        yield from ()
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        try:
            yield DiscrepancyLogEntry.from_dict(data)
        except (jsonschema.ValidationError, ValueError, KeyError, TypeError):
            continue


def iter_publishing_ledger(path: Path) -> Iterator[PublishingLedgerEntry]:
    if not path.is_file():
        yield from ()
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        entry = _parse_publishing_row(data)
        if entry is not None:
            yield entry


def _parse_publishing_row(data: dict[str, Any]) -> PublishingLedgerEntry | None:
    if "entity_id" in data and "entity_type" in data and "timestamp" in data:
        return PublishingLedgerEntry.from_dict(data)
    legacy_id = data.get("version_id") or data.get("entity_id")
    if not legacy_id:
        return None
    ts = data.get("timestamp") or data.get("ts")
    if not ts:
        return None
    new_row = {
        "timestamp": str(ts),
        "entity_id": str(legacy_id),
        "entity_type": "version",
    }
    return PublishingLedgerEntry.from_dict(new_row)


def publishing_ledger_index_by_entity_id(path: Path) -> dict[str, PublishingLedgerEntry]:
    seen: dict[str, PublishingLedgerEntry] = {}
    for entry in iter_publishing_ledger(path):
        seen[entry.entity_id] = entry
    return seen
