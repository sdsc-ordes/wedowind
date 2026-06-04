"""CLI: push CKAN-derived OEMetadata to OEP for configured package_search sources."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from omi.base import MetadataError

from mappers.checkpoint_state import advance_source_state, canonical_checkpoint, filter_new_datasets
from mappers.ckan.helpers import iter_package_search_results
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
    """Build the CLI argument parser for batch CKAN publish.

    Returns
    -------
    argparse.ArgumentParser
        Parser with source, overlap, OEP, and dry-run options.
    """
    parser = argparse.ArgumentParser(
        description="Map CKAN datasets from configured queries to OEMetadata and publish to OEP."
    )
    parser.add_argument("--sources-path", default=str(DEFAULT_SOURCES_PATH))
    parser.add_argument("--timestamp-path", default=str(DEFAULT_TIMESTAMP_PATH))
    parser.add_argument("--source-id", default=None)
    parser.add_argument("--overlap-hours", type=int, default=24)
    add_oep_publish_cli_args(parser)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _oep_defaults_for_source(entry: dict[str, Any]):
    """Parse OEP defaults from one CKAN source config entry.

    Parameters
    ----------
    entry : dict
        Single source block from the CKAN sources registry.

    Returns
    -------
    OepDefaults
        Parsed defaults with provenance label ``"ckan"``.
    """
    return parse_oep_defaults(entry.get("oep"), provenance_label="ckan")


def main() -> int:
    """Map new CKAN packages from configured queries and publish to OEP.

    Returns
    -------
    int
        ``0`` when all packages are processed successfully, ``1`` on map or
        publish failure.

    Raises
    ------
    SystemExit
        When no sources are configured, an unknown ``--source-id`` is given, or
        the OEP API token is missing in non-dry-run mode.
    """
    load_dotenv_if_available()
    args = build_parser().parse_args()
    sources_path = Path(args.sources_path).expanduser().resolve()
    timestamp_path = Path(args.timestamp_path).expanduser().resolve()

    cfg = load_ckan_sources(path=sources_path)
    sources = cfg.get("sources") or {}
    if not sources:
        raise SystemExit("No CKAN sources configured.")

    state = load_ckan_timestamp_state(path=timestamp_path, sources_path=sources_path)
    token = oep_api_token(args.token)
    if not args.dry_run and not token:
        raise SystemExit("Missing OEP token: pass --token or set OEP_API_TOKEN.")

    source_items = sorted(sources.items())
    if args.source_id:
        sid = str(args.source_id).strip()
        if sid not in sources:
            raise SystemExit(f"Unknown source id: {sid!r}")
        source_items = [(sid, sources[sid])]

    total_published = 0
    for source_id, entry in source_items:
        if not isinstance(entry, dict):
            continue
        base_url = str((entry.get("api") or {}).get("base_url") or "").strip()
        if not base_url:
            continue

        oep_defaults = apply_oep_cli_overrides(_oep_defaults_for_source(entry), args)
        mapper = CKANToOepMapper(base_url, source_key=source_id)

        for query in entry.get("queries") or []:
            if not isinstance(query, dict):
                continue
            query_id = query.get("id")
            if not isinstance(query_id, str) or not query_id.strip():
                continue
            search_params = query.get("package_search")
            if not isinstance(search_params, dict) or not search_params:
                continue

            pkgs = list(iter_package_search_results(mapper.ckan, search_params))
            records = [
                {"id": str(p.get("name") or ""), "updated": str(p.get("metadata_modified") or "")}
                for p in pkgs
                if isinstance(p, dict) and p.get("name")
            ]

            sources_top = state.setdefault("sources", {})
            src_block = sources_top.setdefault(source_id, {"queries": {}})
            queries_map = src_block.setdefault("queries", {})
            query_state = canonical_checkpoint(queries_map.get(query_id))
            to_process = [
                r
                for r in filter_new_datasets(records, query_state, overlap_hours=args.overlap_hours)
                if str(r.get("id") or "").strip()
            ]

            for rec in to_process:
                dataset_id = str(rec.get("id") or "").strip()
                try:
                    metadata = mapper.map_to_oemetadata(dataset_id, oep_defaults)
                except Exception as err:
                    print(f"[ckan:oep] map failed: {err}", flush=True)
                    return 1

                if not args.skip_validation:
                    validate_oemetadata(metadata)

                if args.dry_run:
                    if oep_defaults.ensure_tables:
                        publish_to_oep(
                            metadata,
                            token=token or "dry-run",
                            ensure_tables=True,
                            dry_run=True,
                        )
                    continue

                try:
                    publish_to_oep(
                        metadata,
                        token=token or "",
                        method=args.method,
                        ensure_tables=oep_defaults.ensure_tables,
                    )
                except (MetadataError, OepTableProvisionError) as err:
                    print(f"[ckan:oep] publish failed: {err}", flush=True)
                    return 1

                pkg = mapper._last_package or {}
                query_state = advance_source_state(
                    query_state,
                    [
                        {
                            "id": dataset_id,
                            "updated": str(pkg.get("metadata_modified") or rec.get("updated") or ""),
                        }
                    ],
                    run_at=datetime.now(UTC),
                )
                queries_map[query_id] = query_state
                save_ckan_timestamp_state(state, path=timestamp_path, enabled=not args.dry_run)
                total_published += 1

    print(f"[ckan:oep] done. published={total_published}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
