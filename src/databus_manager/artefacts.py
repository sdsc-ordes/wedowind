"""
Artefact-level discovery and registration (template stubs).

Extension points:
- Mirror :mod:`databus_manager.groups` for POSTing ``artefact-metadata.jsonld``.
- Enforce ordering: register artefacts after their parent group exists on Databus.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from databus_manager.common_core import (
    find_child_dirs_with_metadata,
    load_jsonld_file,
    stub_register_metadata_result,
)


ARTEFACT_METADATA_NAME = "artefact-metadata.jsonld"
ARTEFACT_DIR_PREFIX = "artefacts-"


def find_artefact_dirs(group_dir: Path) -> list[Path]:
    """Return ``artefacts-*`` directories under a group folder."""
    return find_child_dirs_with_metadata(
        group_dir,
        metadata_filename=ARTEFACT_METADATA_NAME,
        name_prefix=ARTEFACT_DIR_PREFIX,
        exclude_hidden=True,
    )


def load_artefact_metadata(artefact_dir: Path) -> dict[str, Any]:
    return load_jsonld_file(artefact_dir, ARTEFACT_METADATA_NAME)


def register_artefact(
    artefact_dir: Path,
    *,
    api_key: str | None,
    dry_run: bool,
) -> dict[str, Any]:
    """Publish artefact metadata (stub)."""
    payload = load_artefact_metadata(artefact_dir)
    return stub_register_metadata_result(
        kind="artefact",
        entity_dir=artefact_dir,
        payload=payload,
        dry_run=dry_run,
        api_key=api_key,
        replace_instruction=(
            "Replace databus_manager.artefacts.register_artefact with a real HTTP register call."
        ),
    )
