"""JSON-schema-backed publishing log entries for local catalog publishing."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import jsonschema
from jsonschema import Draft202012Validator

PublishingEntityType = Literal["version"]


def schemas_dir() -> Path:
    """Bundled JSON schemas under ``databus_local_manager/schemas``."""
    databus_pkg = Path(__file__).resolve().parent
    packaged = databus_pkg / "schemas"
    if packaged.is_dir():
        return packaged
    dev = databus_pkg.parent / "schemas"
    if dev.is_dir():
        return dev
    raise FileNotFoundError("JSON schemas not found; expected databus_local_manager/schemas.")


def _load_schema(name: str) -> dict[str, Any]:
    """Load a JSON schema dict from the bundled ``schemas`` directory."""
    path = schemas_dir() / name
    return json.loads(path.read_text(encoding="utf-8"))


_publishing_validator = Draft202012Validator(_load_schema("publishing.schema.json"))


def validate_publishing(instance: dict[str, Any]) -> None:
    """Validate ``instance`` against ``publishing.schema.json``."""
    _publishing_validator.validate(instance)


@dataclass(frozen=True)
class PublishingEntry:
    """One append-only publishings log line (validated on construction)."""

    timestamp: str
    entity_id: str
    entity_type: PublishingEntityType

    def __post_init__(self) -> None:
        """Validate this entry against the publishing schema."""
        validate_publishing(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the JSON object written as one JSONL line."""
        return {
            "timestamp": self.timestamp,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PublishingEntry:
        """Parse and validate a JSON object from a log line."""
        validate_publishing(data)
        return cls(
            timestamp=str(data["timestamp"]),
            entity_id=str(data["entity_id"]),
            entity_type="version",
        )


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def iter_publishings(path: Path) -> Iterator[PublishingEntry]:
    """Yield valid :class:`PublishingEntry` rows from ``path`` (skip bad lines)."""
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
            yield PublishingEntry.from_dict(data)
        except (jsonschema.ValidationError, KeyError, TypeError):
            continue


def publishings_index_by_entity_id(path: Path) -> dict[str, PublishingEntry]:
    """Map ``entity_id`` → latest entry (last line wins)."""
    seen: dict[str, PublishingEntry] = {}
    for entry in iter_publishings(path):
        seen[entry.entity_id] = entry
    return seen
