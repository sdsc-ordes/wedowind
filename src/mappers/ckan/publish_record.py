"""CLI: publish a single CKAN dataset and patch one query checkpoint."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from databus_local_manager.load_env import load_dotenv_if_available
from mappers.checkpoint_state import canonical_checkpoint
from mappers.ckan.manage_sources import (
    DEFAULT_SOURCES_PATH,
    DEFAULT_TIMESTAMP_PATH,
    load_ckan_timestamp_state,
    save_ckan_timestamp_state,
)
from mappers.ckan.mapper import CKANToDataBusMapper
from mappers.databus import databus_api_key, post_register_payload
from mappers.utils import GroupMetadata, add_databus_publish_cli_args


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for ``python -m mappers.ckan.publish_record``.

    Returns
    -------
    argparse.ArgumentParser
        Parser with CKAN URL, dataset id, group fields, source/query ids, Databus args.
    """
    parser = argparse.ArgumentParser(description="Publish one CKAN dataset to Databus via mapper.")
    parser.add_argument("--ckan-url", required=True, help="CKAN base URL.")
    parser.add_argument("--dataset-id", required=True, help="CKAN dataset ID for package_show.")
    parser.add_argument(
        "--group-name", required=True, help="Databus group slug used in identifier."
    )
    parser.add_argument("--group-title", required=True, help="Databus group title.")
    parser.add_argument("--group-abstract", required=True, help="Databus group abstract.")
    parser.add_argument("--group-description", required=True, help="Databus group description.")
    parser.add_argument(
        "--source-id",
        default="world-bank-group",
        help="Top-level CKAN source key in config/timestamp files.",
    )
    parser.add_argument(
        "--query-id",
        default="wind-topic-datasets",
        help="Query entry id under that source (timestamp bookkeeping).",
    )
    add_databus_publish_cli_args(parser)
    parser.add_argument(
        "--sources-path",
        default=str(DEFAULT_SOURCES_PATH),
        help=f"CKAN sources JSON (used to align timestamp checkpoint keys; default: {DEFAULT_SOURCES_PATH}).",
    )
    parser.add_argument(
        "--timestamp-path",
        default=str(DEFAULT_TIMESTAMP_PATH),
        help=f"Path to CKAN mapper timestamp JSON (default: {DEFAULT_TIMESTAMP_PATH}).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Build payload only, do not POST.")
    return parser


def main() -> int:
    """Publish one CKAN dataset and merge the matching query checkpoint.

    Returns
    -------
    int
        ``0`` on success, ``1`` if Databus POST fails.

    Raises
    ------
    SystemExit
        When API key is required but missing (non-dry-run).
    """
    load_dotenv_if_available()
    args = build_parser().parse_args()
    sources_path = Path(args.sources_path).expanduser().resolve()
    timestamp_path = Path(args.timestamp_path).expanduser().resolve()
    group = GroupMetadata(
        name=args.group_name,
        title=args.group_title,
        abstract=args.group_abstract,
        description=args.group_description,
    )
    mapper = CKANToDataBusMapper(args.ckan_url)
    payload = mapper.map_to_databus_dataset(args.dataset_id, group)
    print(f"[mapper:ckan] prepared version: {payload.get('@id') or payload.get('version_id')}")
    if args.dry_run:
        print("[mapper:ckan] dry-run enabled; skipping publish.")
        return 0

    api_key = databus_api_key(args.api_key)
    if not api_key:
        raise SystemExit("Missing API key: pass --api-key or set DATABUS_API_KEY.")
    try:
        post_register_payload(payload, api_key=api_key, register_url=args.register_url)
    except RuntimeError as err:
        print("[mapper:ckan] publish failed:")
        print(str(err))
        return 1
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    state = load_ckan_timestamp_state(
        path=timestamp_path,
        sources_path=sources_path,
    )
    sources_top = state.setdefault("sources", {})
    src_block = sources_top.setdefault(args.source_id, {"queries": {}})
    queries = src_block.setdefault("queries", {})
    query_state = canonical_checkpoint(queries.get(args.query_id))
    queries[args.query_id] = query_state
    pkg = getattr(mapper, "_last_ckan_package", None) or {}
    modified = pkg.get("metadata_modified")
    query_state["last_run_at"] = now
    query_state["last_seen_dataset_id"] = args.dataset_id
    if modified:
        query_state["last_seen_updated"] = str(modified)
    processed = query_state.get("processed_dataset_ids")
    if not isinstance(processed, list):
        processed = []
    dataset_id = str(args.dataset_id)
    if dataset_id in processed:
        processed = [dataset_id, *[entry for entry in processed if entry != dataset_id]]
    else:
        processed = [dataset_id, *processed]
    query_state["processed_dataset_ids"] = processed[:500]

    save_ckan_timestamp_state(state, path=timestamp_path)
    print(f"[mapper:ckan] updated timestamp state: {timestamp_path}")
    print("[mapper:ckan] published successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
