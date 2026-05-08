#!/usr/bin/env python3
"""Publish local catalog group JSON entries to Databus using publishings-log newness."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import requests

from databus_local_manager.load_env import load_dotenv_if_available
from databus_local_manager.logs import (
    PublishingEntry,
    append_jsonl,
    publishings_index_by_entity_id,
)
from databus_local_manager.parse import build_publish_local_catalog_parser
from databus_local_manager.prepare_metadata import (
    PreparedVersion,
    prepare_group_versions,
)
from databus_local_manager.scan_catalog import scan_catalog

DEFAULT_REGISTER_URL = "https://databus.openenergyplatform.org/api/register"


class RegisterPublishError(Exception):
    """Register endpoint returned a non-success status (response body often contains SHACL errors)."""

    def __init__(self, status_code: int, response_text: str) -> None:
        """Store HTTP status and body text."""
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(f"HTTP {status_code}")


def utc_now_iso() -> str:
    """Current UTC time without microseconds, ISO format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _register_payload(dataset_payload: dict, *, api_key: str, register_url: str) -> None:
    """POST ``dataset_payload`` to register or raise :class:`RegisterPublishError`."""
    resp = requests.post(
        register_url,
        json=dataset_payload,
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        timeout=120,
    )
    if not resp.ok:
        raise RegisterPublishError(resp.status_code, resp.text)


def _scan_prepared_versions(catalog_root: Path) -> list[PreparedVersion]:
    """Scan catalog and prepare all dataset versions found under ``groups``."""
    prepared: list[PreparedVersion] = []
    group_files = scan_catalog(catalog_root)
    if not group_files:
        print(
            f"[scan] No group catalog files under {catalog_root / 'groups'} — nothing to publish."
        )
        return prepared

    print(f"[scan] Catalog directory: {catalog_root.resolve()}")
    for group_file in group_files:
        batch = prepare_group_versions(group_file)
        group_label = batch[0].group_title if batch else "(empty group file)"
        print(
            f"[scan]   • {group_file.path.name}: {len(batch)} version(s) prepared "
            f"(group: {group_label})"
        )
        prepared.extend(batch)
    return prepared


def main() -> int:
    """CLI: classify vs publishings log, POST new versions, append JSONL."""
    load_dotenv_if_available()
    args = build_publish_local_catalog_parser().parse_args()

    catalog_root = Path(args.catalog)
    publishings_path = Path(args.publishings)
    if not catalog_root.is_dir():
        raise SystemExit(f"Catalog root not found: {catalog_root}")

    prepared = _scan_prepared_versions(catalog_root)
    scanned_groups = len({p.group_id for p in prepared})
    scanned_artifacts = len({p.artifact_id for p in prepared})
    scanned_versions = len(prepared)
    print(
        f"[scan] Summary: {scanned_groups} group(s), {scanned_artifacts} artifact(s), "
        f"{scanned_versions} dataset version(s) ready."
    )

    publishings_map = publishings_index_by_entity_id(publishings_path)
    published_versions = [p for p in prepared if p.version_id in publishings_map]
    new_versions = [p for p in prepared if p.version_id not in publishings_map]
    print(
        f"[classify] Compared with publishings log ({publishings_path}): "
        f"{len(published_versions)} already published, {len(new_versions)} new."
    )
    if published_versions:
        print("[classify] Already registered (skipped):")
        _max_skip_lines = 12
        for p in published_versions[:_max_skip_lines]:
            label = p.version_title or p.version_id
            print(f"[classify]   • {label}")
            print(f"[classify]     {p.version_id}")
        extra = len(published_versions) - _max_skip_lines
        if extra > 0:
            print(f"[classify]   … and {extra} more version(s) already in the publishings log.")

    if args.dry_run:
        print("[dry-run] No HTTP POST to Databus; publishings log will not be modified.")
        if new_versions:
            print(f"[dry-run] Would register {len(new_versions)} new dataset version(s):")
            for i, item in enumerate(new_versions, start=1):
                print(f"[dry-run]   {i}. {item.version_title or '(no title)'}")
                print(f"[dry-run]      Source: {item.source_file}")
                print(f"[dry-run]      Version URI: {item.version_id}")
        else:
            print("[dry-run] Nothing new to register — all versions are in the publishings log.")
        return 0

    if not new_versions:
        print("[publish] Nothing new to publish — catalog is up to date.")
        return 0

    api_key = args.api_key or os.getenv("DATABUS_API_KEY")
    if not api_key:
        raise SystemExit("Missing API key: pass --api-key or set DATABUS_API_KEY.")

    total = len(new_versions)
    print(f"[publish] Sending {total} dataset payload(s) to register API ({args.register_url}) …")

    for n, item in enumerate(new_versions, start=1):
        title = item.version_title or "(no title)"
        print(f"[publish] ({n}/{total}) {title}")
        print(f"[publish]     Version URI: {item.version_id}")
        print(f"[publish]     From file: {item.source_file}")
        try:
            _register_payload(item.dataset_payload, api_key=api_key, register_url=args.register_url)
        except RegisterPublishError as err:
            print("[publish] Failed for version URI above.", flush=True)
            print(err.response_text, flush=True)
            return 1
        append_jsonl(
            publishings_path,
            PublishingEntry(
                timestamp=utc_now_iso(),
                entity_id=item.version_id,
                entity_type="version",
            ).to_dict(),
        )
        print("[publish]     Success — appended to publishings log.")

    print(f"[publish] Finished. Updated log: {publishings_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
