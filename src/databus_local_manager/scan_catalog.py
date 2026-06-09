"""Discover per-group JSON files under a catalog directory."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CatalogGroupFile:
    """One ``catalog/groups/*.json`` file and its parsed object."""

    path: Path
    payload: dict[str, Any]


def scan_catalog(catalog_root: Path) -> list[CatalogGroupFile]:
    """Return sorted ``catalog/groups/*.json`` payloads under ``catalog_root``."""
    groups_dir = catalog_root / "groups"
    if not groups_dir.is_dir():
        return []
    entries: list[CatalogGroupFile] = []
    for group_file in sorted(groups_dir.glob("*.json"), key=lambda p: str(p)):
        payload = json.loads(group_file.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            entries.append(CatalogGroupFile(path=group_file, payload=payload))
    return entries
