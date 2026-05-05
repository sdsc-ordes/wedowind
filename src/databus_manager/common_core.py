"""
Shared helpers for catalog discovery and stub registration responses.

Extension points live in domain modules; this module only factors repeated mechanics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from databus_manager import config


def find_child_dirs_with_metadata(
    parent: Path,
    *,
    metadata_filename: str,
    name_prefix: str | None = None,
    exclude_hidden: bool = True,
) -> list[Path]:
    """
    Return immediate child directories that contain ``metadata_filename``.

    If ``name_prefix`` is set, directory names must start with that prefix (e.g.
    ``artefacts-``, ``version-``). If ``name_prefix`` is ``None``, any non-hidden
    subdirectory is considered (used for group folders under ``catalog/``).
    """
    if not parent.is_dir():
        return []
    found: list[Path] = []
    for child in sorted(parent.iterdir()):
        if not child.is_dir():
            continue
        if exclude_hidden and child.name.startswith("."):
            continue
        if name_prefix is not None and not child.name.startswith(name_prefix):
            continue
        if (child / metadata_filename).is_file():
            found.append(child)
    return found


def load_jsonld_file(directory: Path, metadata_filename: str) -> dict[str, Any]:
    """Load a JSON-LD JSON file from ``directory / metadata_filename``."""
    path = directory / metadata_filename
    return json.loads(path.read_text(encoding="utf-8"))


def stub_register_metadata_result(
    *,
    kind: str,
    entity_dir: Path,
    payload: dict[str, Any],
    dry_run: bool,
    api_key: str | None,
    replace_instruction: str,
) -> dict[str, Any]:
    """Build the standard stub response for register_* functions (no HTTP until implemented)."""
    result: dict[str, Any] = {
        "kind": kind,
        "path": str(entity_dir),
        "dry_run": dry_run,
        "register_url": config.REGISTER_URL,
        "status": "skipped_stub",
        "message": replace_instruction,
    }
    if dry_run:
        result["would_send_graph_nodes"] = len(payload.get("@graph", []))
    else:
        _ = api_key
        result["status"] = "not_implemented"
    return result
