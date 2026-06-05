"""CLI: push Zenodo-derived OEMetadata to OEP for configured sources."""

from __future__ import annotations

import argparse
from pathlib import Path

from omi.base import MetadataError
from omi.validation import ValidationError

from mappers.checkpoint_state import advance_source_state, filter_new_datasets
from mappers.load_env import load_dotenv_if_available
from mappers.oep.api import oep_api_token, publish_to_oep, validate_oemetadata
from mappers.oep.oep_defaults import apply_oep_cli_overrides, parse_oep_defaults
from mappers.oep.oep_table import OepTableProvisionError
from mappers.oep.utils import add_oep_publish_cli_args
from mappers.zenodo.manage_sources import (
    DEFAULT_SOURCES_PATH,
    DEFAULT_TIMESTAMP_PATH,
    SOURCE_QUERY_PARAMS,
    load_source_config,
    load_timestamp_state,
    save_timestamp_state,
)
from mappers.zenodo.oep_mapper import ZenodoToOepMapper


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for batch Zenodo publish.

    Returns
    -------
    argparse.ArgumentParser
        Parser with source, pagination, OEP, and dry-run options.
    """
    parser = argparse.ArgumentParser(
        description="Map new Zenodo records to OEMetadata and publish to the Open Energy Platform."
    )
    parser.add_argument("--sources-path", default=str(DEFAULT_SOURCES_PATH))
    parser.add_argument("--timestamp-path", default=str(DEFAULT_TIMESTAMP_PATH))
    parser.add_argument("--overlap-hours", type=int, default=24)
    parser.add_argument("--page-size", type=int, default=100)
    add_oep_publish_cli_args(parser)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    """Map new Zenodo records from configured sources and publish to OEP.

    Returns
    -------
    int
        ``0`` when all records are processed successfully, ``1`` on map,
        validation, or publish failure.

    Raises
    ------
    SystemExit
        When the OEP API token is missing in non-dry-run mode.
    """
    load_dotenv_if_available()
    args = build_parser().parse_args()

    config = load_source_config(path=Path(args.sources_path))
    sources = config["sources"]
    SOURCE_QUERY_PARAMS.clear()
    SOURCE_QUERY_PARAMS.update(sources)
    oep_defaults = apply_oep_cli_overrides(
        parse_oep_defaults(config.get("defaults", {}).get("oep"), provenance_label="zenodo"),
        args,
    )

    timestamp_path = Path(args.timestamp_path)
    state = load_timestamp_state(path=timestamp_path)
    token = oep_api_token(args.token)
    if not args.dry_run and not token:
        raise SystemExit("Missing OEP token: pass --token or set OEP_API_TOKEN.")

    total_published = 0
    for source_key in sources:
        mapper = ZenodoToOepMapper(source_key=source_key)
        source_state = state.get(source_key) or {}

        page = 1
        records: list[dict] = []
        while True:
            batch = mapper.client.fetch_source_records(source_key, page=page, size=args.page_size)
            if not batch:
                break
            records.extend(batch)
            page += 1

        hits = [
            r
            for r in filter_new_datasets(records, source_state, overlap_hours=args.overlap_hours)
            if str(r.get("id") or "").strip()
        ]

        for idx, rec in enumerate(hits, start=1):
            dataset_id = str(rec.get("id") or "").strip()
            print(f"[zenodo:oep] ({idx}/{len(hits)}) map id={dataset_id} …", flush=True)
            try:
                metadata = mapper.map_to_oemetadata(dataset_id, oep_defaults)
            except Exception as err:
                print(f"[zenodo:oep] map failed: {err}", flush=True)
                return 1

            if not args.skip_validation:
                try:
                    validate_oemetadata(metadata)
                except ValidationError as err:
                    print(f"[zenodo:oep] validation failed: {err}", flush=True)
                    return 1

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
                print(f"[zenodo:oep] publish failed: {err}", flush=True)
                return 1

            source_state = advance_source_state(source_state, [rec])
            state[source_key] = source_state
            save_timestamp_state(state, path=timestamp_path, enabled=not args.dry_run)
            total_published += 1

    print(f"[zenodo:oep] done. published={total_published}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
