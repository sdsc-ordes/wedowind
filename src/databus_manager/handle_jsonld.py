"""JSON-LD file parsing and version URI helpers for the catalog layout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_graph_node(doc: dict[str, Any], expected_type: str) -> dict[str, Any]:
    graph = doc.get("@graph")
    if not isinstance(graph, list):
        raise ValueError(f"Invalid @graph in {expected_type} document.")
    for node in graph:
        t = node.get("@type")
        if t == expected_type or (isinstance(t, list) and expected_type in t):
            return node
    raise ValueError(f"No @graph node with @type '{expected_type}' found.")


def version_id_to_group_id(version_id: str) -> str:
    return version_id.rsplit("/", 2)[0]


def version_id_to_artefact_id(version_id: str) -> str:
    """Artifact URI: version ``@id`` without the final version segment."""
    return version_id.rsplit("/", 1)[0]
