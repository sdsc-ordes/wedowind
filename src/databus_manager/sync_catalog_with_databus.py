#!/usr/bin/env python3
"""Databus-first sync orchestration: compare/pull, classify, publish new, update ledger."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from databus_manager.compare_catalog_with_databus import compare_and_pull
from databus_manager.sparql import sparql_remote_version_exists
from databus_manager.objects.logs import (
    PublishingLedgerEntry,
    append_jsonl,
    publishing_ledger_index_by_entity_id,
)
from databus_manager.scan_catalog import scan_catalog
from databus_manager.parse import build_sync_catalog_parser
from databus_manager.publish_group_metadata import publish


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def classify_entries(
    catalog_root: Path,
    *,
    ledger_map: dict[str, PublishingLedgerEntry],
    sparql_url: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in scan_catalog(catalog_root):
        exists_remote = sparql_remote_version_exists(entry.version_id, sparql_url)
        in_ledger = entry.version_id in ledger_map
        if exists_remote and in_ledger:
            status = "published"
        elif exists_remote and not in_ledger:
            status = "ledger_mismatch"
        else:
            status = "new"
        rows.append(
            {
                "version_id": entry.version_id,
                "group_id": entry.group_id,
                "version_file": str(entry.version_file),
                "status": status,
                "remote_exists": exists_remote,
                "in_ledger": in_ledger,
            }
        )
    return rows


def main() -> int:
    args = build_sync_catalog_parser().parse_args()

    catalog_root = Path(args.catalog)
    ledger_path = Path(args.ledger)
    discrepancy_path = Path(args.discrepancy_log)
    if not catalog_root.is_dir():
        raise SystemExit(f"Catalog root not found: {catalog_root}")
    api_key = args.api_key or os.getenv("DATABUS_API_KEY")

    detection_timestamp = utc_now_iso()
    compare_rows = compare_and_pull(
        catalog_root,
        sparql_url=args.sparql_url,
        apply_changes=(not args.dry_run),
        detection_timestamp=detection_timestamp,
    )
    print(f"[compare] scanned versions: {len(compare_rows)}")
    print(
        "[compare] mismatches: "
        f"{sum(1 for r in compare_rows if r['version_mismatch'] or r['group_mismatch'] or r['artefact_mismatch'])}"
    )

    for row in compare_rows:
        for disc in row.get("discrepancy_entries") or []:
            append_jsonl(discrepancy_path, disc)

    ledger_map = publishing_ledger_index_by_entity_id(ledger_path)
    classifications = classify_entries(catalog_root, ledger_map=ledger_map, sparql_url=args.sparql_url)
    new_rows = [r for r in classifications if r["status"] == "new"]
    mismatch_rows = [r for r in classifications if r["status"] == "ledger_mismatch"]

    print(f"[classify] published: {len(classifications) - len(new_rows) - len(mismatch_rows)}")
    print(f"[classify] ledger_mismatch: {len(mismatch_rows)}")
    print(f"[classify] new: {len(new_rows)}")

    if args.pull_only:
        print("[mode] pull-only enabled; skipping publish.")
        return 0

    if args.dry_run:
        print("[mode] dry-run enabled; skipping publish and ledger updates.")
        return 0
    if not api_key:
        raise SystemExit("Missing API key: pass --api-key or set DATABUS_API_KEY.")

    for row in new_rows:
        version_file = Path(row["version_file"])
        publish(version_file, api_key=api_key, register_url=args.register_url)
        append_jsonl(
            ledger_path,
            PublishingLedgerEntry(
                timestamp=utc_now_iso(),
                entity_id=row["version_id"],
                entity_type="version",
            ).to_dict(),
        )
        print(f"[publish] published new version: {row['version_id']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
