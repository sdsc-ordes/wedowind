"""
Group-level discovery and registration (template stubs).

Extension points:
- Implement :func:`register_group` to POST ``group-metadata.jsonld`` payloads to
  :data:`databus_manager.config.REGISTER_URL` with header ``X-API-KEY``.
- Add existence checks (SPARQL ASK/SELECT) before publishing if your workflow
  requires collision detection with manual UI uploads.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from databus_manager.common_core import (
    find_child_dirs_with_metadata,
    load_jsonld_file,
    stub_register_metadata_result,
)


GROUP_METADATA_NAME = "group-metadata.jsonld"


def find_group_dirs(catalog_root: Path) -> list[Path]:
    """Return immediate subdirectories of ``catalog`` that look like group folders."""
    return find_child_dirs_with_metadata(
        catalog_root,
        metadata_filename=GROUP_METADATA_NAME,
        name_prefix=None,
        exclude_hidden=True,
    )


def load_group_metadata(group_dir: Path) -> dict[str, Any]:
    return load_jsonld_file(group_dir, GROUP_METADATA_NAME)


def register_group(
    group_dir: Path,
    *,
    api_key: str | None,
    dry_run: bool,
) -> dict[str, Any]:
    """
    Publish group metadata to Databus (stub: records intent only).

    Replace this body with ``httpx.post(config.REGISTER_URL, ...)`` using
    ``Content-Type: application/json`` and the document loaded from
    ``group-metadata.jsonld``.
    """
    payload = load_group_metadata(group_dir)
    return stub_register_metadata_result(
        kind="group",
        entity_dir=group_dir,
        payload=payload,
        dry_run=dry_run,
        api_key=api_key,
        replace_instruction=(
            "Replace databus_manager.groups.register_group with a real HTTP register call."
        ),
    )
