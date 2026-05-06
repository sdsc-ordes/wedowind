#!/usr/bin/env python3
"""Databus-first sync orchestration: compare/pull, classify, publish new, append publishings."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from databus_manager.compare_catalog_with_databus import compare_and_pull
from databus_manager.load_env import load_dotenv_if_available
from databus_manager.sparql import sparql_remote_version_exists
from databus_manager.objects.logs import (
    PublishingEntry,
    append_jsonl,
    publishings_index_by_entity_id,
)
from databus_manager.objects.metadata import CatalogVersionRef
from databus_manager.scan_catalog import scan_catalog
from databus_manager.parse import build_sync_catalog_parser
from databus_manager.publish_group_metadata import RegisterPublishError, publish


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


_CLASSIFY_STATUS_NOTE: dict[str, str] = {
    "published": "this version URI exists on Databus and local publishings lists it",
    "publishings_mismatch": (
        "this version URI exists on Databus but publishings has no row "
        "(published elsewhere / publishings drift)"
    ),
    "new": "this version URI not on Databus yet (publish candidate); unrelated to [compare] metadata mismatches",
}


def classify_entries(
    catalog_root: Path,
    *,
    publishings_map: dict[str, PublishingEntry],
    sparql_url: str,
    scanned: list[CatalogVersionRef] | None = None,
) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    entries = scanned if scanned is not None else scan_catalog(catalog_root)
    for entry in entries:
        exists_remote = sparql_remote_version_exists(entry.version_id, sparql_url)
        in_publishings = entry.version_id in publishings_map
        if exists_remote and in_publishings:
            status = "published"
        elif exists_remote and not in_publishings:
            status = "publishings_mismatch"
        else:
            status = "new"
        entities.append(
            {
                "version_id": entry.version_id,
                "group_id": entry.group_id,
                "artifact_id": entry.artifact_id,
                "group_file": str(entry.group_file),
                "artifact_file": str(entry.artifact_file),
                "version_file": str(entry.version_file),
                "status": status,
                "remote_version_exists": exists_remote,
                "in_publishings": in_publishings,
            }
        )
    return entities


def _path_relative_to_catalog_root(catalog_root: Path, path: Path | str) -> str:
    anchor = catalog_root.resolve()
    p = Path(path).resolve()
    try:
        return str(p.relative_to(anchor))
    except ValueError:
        return str(p)


def _discrepancy_counts_by_entity(discrepancy_entries: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"group": 0, "artifact": 0, "version": 0}
    for row in discrepancy_entries:
        et = row.get("entity_type")
        if et in counts:
            counts[str(et)] += 1
    return counts


def _version_display_from_path(version_file: Path) -> str:
    """Version directories use ``v<semver>/`` (e.g. ``v1.2.0``)."""
    return version_file.parent.name


def _compare_entity_line(
    *,
    kind: str,
    display_name: str,
    remote_exists: bool,
    mismatch: bool,
    discrepancy_n: int,
) -> str:
    remote_bit = "on Databus" if remote_exists else "not on Databus"
    if mismatch:
        disc_bit = (
            f"mismatch; {discrepancy_n} discrepancy field(s) logged"
            if discrepancy_n
            else "mismatch"
        )
    else:
        disc_bit = "no mismatch"
        if discrepancy_n:
            disc_bit += f"; {discrepancy_n} discrepancy field(s) logged"
    return f"[compare]            {kind}: {display_name} — {remote_bit} — {disc_bit}"


def _log_compare_entities(catalog_root: Path, compare_entities: list[dict[str, Any]]) -> None:
    """Human-readable lines for compare/pull (group + artifact + version vs remote SPARQL)."""
    n = len(compare_entities)
    noun = "entity" if n == 1 else "entities"
    print(f"[compare] detail - metadata checked per version (group, artifact, version vs Databus): {n} {noun}")
    if not compare_entities:
        print("[compare]   (none)")
        return
    for idx, entity in enumerate(compare_entities, 1):
        vf_path = Path(entity["version_file"])
        vf = _path_relative_to_catalog_root(catalog_root, entity["version_file"])
        discs = _discrepancy_counts_by_entity(entity.get("discrepancy_entries") or [])
        group_folder = Path(entity["group_file"]).parent.name
        artifact_folder = Path(entity["artifact_file"]).parent.name
        version_display = _version_display_from_path(vf_path)

        print(f"[compare]   [{idx}/{n}] {vf}")
        print(
            _compare_entity_line(
                kind="group",
                display_name=group_folder,
                remote_exists=bool(entity["remote_group_exists"]),
                mismatch=bool(entity["group_mismatch"]),
                discrepancy_n=discs["group"],
            )
        )
        print(
            _compare_entity_line(
                kind="artifact",
                display_name=artifact_folder,
                remote_exists=bool(entity["remote_artifact_exists"]),
                mismatch=bool(entity["artifact_mismatch"]),
                discrepancy_n=discs["artifact"],
            )
        )
        print(
            _compare_entity_line(
                kind="version",
                display_name=version_display,
                remote_exists=bool(entity["remote_version_exists"]),
                mismatch=bool(entity["version_mismatch"]),
                discrepancy_n=discs["version"],
            )
        )
        if entity.get("changed_local_from_remote"):
            print("[compare]            pulled remote metadata into local catalog files (apply_changes)")


def _log_classify_entities(catalog_root: Path, classified_entities: list[dict[str, Any]]) -> None:
    n = len(classified_entities)
    noun = "entity" if n == 1 else "entities"
    print(f"[classify] detail - SPARQL version presence vs local publishings ({n} {noun})")
    if not classified_entities:
        print("[classify]   (none)")
        return
    for idx, entity in enumerate(classified_entities, 1):
        vf = _path_relative_to_catalog_root(catalog_root, entity["version_file"])
        note = _CLASSIFY_STATUS_NOTE[entity["status"]]
        print(f"[classify]   [{idx}/{n}] {vf}")
        print(
            "[classify]            examined: "
            f"remote_version_exists={entity['remote_version_exists']} in_publishings={entity['in_publishings']} "
            f"-> status={entity['status']}"
        )
        print(f"[classify]            {note}")


def main() -> int:
    load_dotenv_if_available()
    args = build_sync_catalog_parser().parse_args()

    catalog_root = Path(args.catalog)
    publishings_path = Path(args.publishings)
    discrepancy_path = Path(args.discrepancy_log)
    if not catalog_root.is_dir():
        raise SystemExit(f"Catalog root not found: {catalog_root}")
    api_key = args.api_key or os.getenv("DATABUS_API_KEY")

    detection_timestamp = utc_now_iso()
    compare_entities, scanned_refs = compare_and_pull(
        catalog_root,
        sparql_url=args.sparql_url,
        apply_changes=(not args.dry_run),
        detection_timestamp=detection_timestamp,
    )
    scanned_groups = len({e["group_id"] for e in compare_entities})
    scanned_artifacts = len({e["artifact_id"] for e in compare_entities})
    scanned_versions = len(compare_entities)
    print(f"[compare] scanned groups: {scanned_groups}")
    print(f"[compare] scanned artifacts: {scanned_artifacts}")
    print(f"[compare] scanned versions: {scanned_versions}")
    print(
        "[compare] mismatches: "
        f"{sum(1 for e in compare_entities if e['version_mismatch'] or e['group_mismatch'] or e['artifact_mismatch'])}"
    )
    _log_compare_entities(catalog_root, compare_entities)

    for entity in compare_entities:
        for disc in entity.get("discrepancy_entries") or []:
            append_jsonl(discrepancy_path, disc)

    publishings_map = publishings_index_by_entity_id(publishings_path)
    classified_entities = classify_entries(
        catalog_root,
        publishings_map=publishings_map,
        sparql_url=args.sparql_url,
        scanned=scanned_refs,
    )
    _log_classify_entities(catalog_root, classified_entities)
    new_entities = [e for e in classified_entities if e["status"] == "new"]
    mismatch_entities = [e for e in classified_entities if e["status"] == "publishings_mismatch"]

    print(f"[classify] published: {len(classified_entities) - len(new_entities) - len(mismatch_entities)}")
    print(f"[classify] publishings_mismatch: {len(mismatch_entities)}")
    print(f"[classify] new: {len(new_entities)}")

    if args.pull_only:
        print("[mode] pull-only enabled; skipping publish.")
        return 0

    if args.dry_run:
        print("[mode] dry-run enabled; skipping publish and publishings updates.")
        return 0
    if not api_key:
        raise SystemExit("Missing API key: pass --api-key or set DATABUS_API_KEY.")

    for entity in new_entities:
        version_file = Path(entity["version_file"])
        try:
            publish(version_file, api_key=api_key, register_url=args.register_url)
        except RegisterPublishError as err:
            print(f"[publish] failed: {entity['version_id']}", flush=True)
            print(err.response_text, flush=True)
            return 1
        append_jsonl(
            publishings_path,
            PublishingEntry(
                timestamp=utc_now_iso(),
                entity_id=entity["version_id"],
                entity_type="version",
            ).to_dict(),
        )
        print(f"[publish] published: {entity['version_id']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
