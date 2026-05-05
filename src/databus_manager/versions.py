"""
Version JSON-LD loading and registration (template stubs).

Extension points:
- Implement POST to :data:`databus_manager.config.REGISTER_URL` with the exact OEP
  headers::

      Content-Type: application/json
      X-API-KEY: <secret>

  Payload shape matches ``version.jsonld`` in each ``version-*`` folder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from databus_manager.common_core import (
    find_child_dirs_with_metadata,
    load_jsonld_file,
    stub_register_metadata_result,
)

VERSION_METADATA_NAME = "version.jsonld"
VERSION_DIR_PREFIX = "version-"


def find_version_dirs(artefact_dir: Path) -> list[Path]:
    """Return ``version-*`` directories under an artefact folder."""
    return find_child_dirs_with_metadata(
        artefact_dir,
        metadata_filename=VERSION_METADATA_NAME,
        name_prefix=VERSION_DIR_PREFIX,
        exclude_hidden=True,
    )


def load_version_payload(version_dir: Path) -> dict[str, Any]:
    return load_jsonld_file(version_dir, VERSION_METADATA_NAME)


def register_version(
    version_dir: Path,
    *,
    api_key: str | None,
    dry_run: bool,
) -> dict[str, Any]:
    """Publish a Version document (stub)."""
    payload = load_version_payload(version_dir)
    return stub_register_metadata_result(
        kind="version",
        entity_dir=version_dir,
        payload=payload,
        dry_run=dry_run,
        api_key=api_key,
        replace_instruction=(
            "Replace databus_manager.versions.register_version with "
            "httpx.post(..., json=payload)."
        ),
    )
