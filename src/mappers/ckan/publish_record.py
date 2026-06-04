"""CLI: push OEMetadata for one CKAN dataset to OEP."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from omi.base import MetadataError

from mappers.checkpoint_state import canonical_checkpoint
from mappers.ckan.manage_sources import (
    DEFAULT_SOURCES_PATH,
    DEFAULT_TIMESTAMP_PATH,
    load_ckan_sources,
    load_ckan_timestamp_state,
    save_ckan_timestamp_state,
)
from mappers.ckan.oep_mapper import CKANToOepMapper
from mappers.load_env import load_dotenv_if_available
from mappers.oep.api import oep_api_token, publish_to_oep, validate_oemetadata
from mappers.oep.oep_defaults import apply_oep_cli_overrides, parse_oep_defaults
from mappers.oep.oep_table import OepTableProvisionError
from mappers.oep.utils import add_oep_publish_cli_args


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for single-package CKAN publish.

    Returns
    -------
    argparse.ArgumentParser
        Parser with CKAN URL, dataset, source, OEP, and dry-run options.
    """
    parser = argparse.ArgumentParser(description="Map one CKAN dataset to OEMetadata and publish to OEP.")
    parser.add_argument("--ckan-url", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--source-id", default="world-bank-group")
    parser.add_argument("--query-id", default="wind-topic-datasets")
    parser.add_argument("--sources-path", default=str(DEFAULT_SOURCES_PATH))
    parser.add_argument("--timestamp-path", default=str(DEFAULT_TIMESTAMP_PATH))
    add_oep_publish_cli_args(parser)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    """Map one CKAN package and publish OEMetadata to OEP.

    Returns
    -------
    int
        ``0`` on success, ``1`` when publish fails.

    Raises
    ------
    SystemExit
        When the OEP API token is missing in non-dry-run mode.
    """
    load_dotenv_if_available()
    args = build_parser().parse_args()
    sources_path = Path(args.sources_path).expanduser().resolve()
    timestamp_path = Path(args.timestamp_path).expanduser().resolve()

    entry = (load_ckan_sources(path=sources_path).get("sources") or {}).get(args.source_id) or {}
    oep_defaults = apply_oep_cli_overrides(
        parse_oep_defaults(entry.get("oep"), provenance_label="ckan"),
        args,
    )

    mapper = CKANToOepMapper(args.ckan_url, source_key=args.source_id)
    metadata = mapper.map_to_oemetadata(args.dataset_id, oep_defaults)

    if not args.skip_validation:
        validate_oemetadata(metadata)

    if args.dry_run:
        if oep_defaults.ensure_tables:
            publish_to_oep(metadata, token="dry-run", ensure_tables=True, dry_run=True)
        return 0

    token = oep_api_token(args.token)
    if not token:
        raise SystemExit("Missing OEP token: pass --token or set OEP_API_TOKEN.")

    try:
        publish_to_oep(
            metadata,
            token=token,
            method=args.method,
            ensure_tables=oep_defaults.ensure_tables,
        )
    except (MetadataError, OepTableProvisionError) as err:
        print(f"[ckan:oep] publish failed: {err}")
        return 1

    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    state = load_ckan_timestamp_state(path=timestamp_path, sources_path=sources_path)
    sources_top = state.setdefault("sources", {})
    src_block = sources_top.setdefault(args.source_id, {"queries": {}})
    queries = src_block.setdefault("queries", {})
    query_state = canonical_checkpoint(queries.get(args.query_id))
    pkg = mapper._last_package or {}
    query_state["last_run_at"] = now
    query_state["last_seen_dataset_id"] = args.dataset_id
    if pkg.get("metadata_modified"):
        query_state["last_seen_updated"] = str(pkg["metadata_modified"])
    did = str(args.dataset_id)
    processed = query_state.get("processed_dataset_ids")
    if not isinstance(processed, list):
        processed = []
    query_state["processed_dataset_ids"] = [did, *[x for x in processed if x != did]][:500]
    queries[args.query_id] = query_state
    save_ckan_timestamp_state(state, path=timestamp_path, enabled=not args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
