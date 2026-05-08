#!/usr/bin/env python3
"""Validate local catalog JSON and prepare databusclient dataset payloads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from databusclient.api.deploy import (
    BadArgumentException,
    create_dataset,
    create_distribution,
)

from databus_local_manager.catalog_schema import validate_catalog_group
from databus_local_manager.parse import build_prepare_metadata_parser
from databus_local_manager.scan_catalog import CatalogGroupFile


@dataclass(frozen=True)
class PreparedVersion:
    """One dataset version ready for Databus register (payload + ids)."""

    source_file: Path
    group_id: str
    group_title: str
    artifact_id: str
    version_id: str
    version_title: str
    dataset_payload: dict[str, Any]


def _build_distributions(parts: list[dict[str, Any]]) -> list[str]:
    """Build databusclient distribution strings for ``version.distributions`` entries."""
    out: list[str] = []
    single = len(parts) == 1
    for idx, part in enumerate(parts):
        url = str(part["downloadURL"])
        file_format = str(part["formatExtension"])
        compression_raw = part.get("compression")
        compression = None
        if isinstance(compression_raw, str) and compression_raw.lower() not in (
            "",
            "none",
        ):
            compression = compression_raw
        cvs: dict[str, str] = {} if single else {"part": str(idx)}
        out.append(
            create_distribution(
                url=url,
                cvs=cvs,
                file_format=file_format,
                compression=compression,
            )
        )
    return out


def prepare_group_versions(group_file: CatalogGroupFile) -> list[PreparedVersion]:
    """Validate group JSON and return one ``PreparedVersion`` per artifact version."""
    validate_catalog_group(group_file.payload)
    group = group_file.payload["group"]
    group_id = str(group["id"])
    group_title = str(group.get("title") or "")
    out: list[PreparedVersion] = []
    for artifact in group_file.payload["artifacts"]:
        artifact_id = str(artifact["id"])
        for version in artifact["versions"]:
            distributions = _build_distributions(version["distributions"])
            version_title = str(version.get("title") or "")
            dataset = create_dataset(
                version_id=str(version["id"]),
                title=str(version["title"]),
                abstract=str(version["abstract"]),
                description=str(version["description"]),
                license_url=str(version["license"]),
                distributions=distributions,
                group_title=str(group["title"]),
                group_abstract=str(group["abstract"]),
                group_description=str(group["description"]),
            )
            out.append(
                PreparedVersion(
                    source_file=group_file.path,
                    group_id=group_id,
                    group_title=group_title,
                    artifact_id=artifact_id,
                    version_id=str(version["id"]),
                    version_title=version_title,
                    dataset_payload=dataset,
                )
            )
    return out


def main() -> int:
    """CLI entry: print prepared payloads for a single group file."""
    args = build_prepare_metadata_parser().parse_args()
    path = Path(args.group_file)
    if not path.is_file():
        raise SystemExit(f"Group file not found: {path}")
    group_file = CatalogGroupFile(
        path=path,
        payload=json.loads(path.read_text(encoding="utf-8")),
    )
    try:
        prepared = prepare_group_versions(group_file)
    except (BadArgumentException, KeyError, TypeError, ValueError) as err:
        raise SystemExit(f"Metadata preparation failed for {path}: {err}") from err

    print(f"[prepare] Group file: {path}")
    if prepared:
        print(f"[prepare] Catalog group: {prepared[0].group_title or '(no title)'}")
        print(f"[prepare] Built {len(prepared)} dataset payload(s) for Databus register.")
        for i, item in enumerate(prepared, start=1):
            print(f"[prepare]   {i}. {item.version_title or '(no title)'}")
            print(f"[prepare]      Version URI: {item.version_id}")
            print(f"[prepare]      Artifact URI: {item.artifact_id}")
    else:
        print("[prepare] No versions found in this group file (nothing to prepare).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
