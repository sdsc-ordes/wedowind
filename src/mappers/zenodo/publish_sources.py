"""CLI: publish Zenodo datasets from configured sources with timestamp checkpoints."""

from __future__ import annotations

import argparse
from pathlib import Path

from databus_local_manager.load_env import load_dotenv_if_available
from mappers.checkpoint_state import advance_source_state, filter_new_datasets
from mappers.databus import databus_api_key, post_register_payload
from mappers.utils import GroupMetadata, add_databus_publish_cli_args
from mappers.zenodo.manage_sources import (
    DEFAULT_SOURCES_PATH,
    DEFAULT_TIMESTAMP_PATH,
    SOURCE_QUERY_PARAMS,
    load_source_config,
    load_timestamp_state,
    save_timestamp_state,
)
from mappers.zenodo.mapper import ZenodoToDataBusMapper


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for ``python -m mappers.zenodo.publish_sources``.

    Returns
    -------
    argparse.ArgumentParser
        Parser with sources/timestamp paths, group overrides, overlap, page size, Databus args.
    """
    parser = argparse.ArgumentParser(
        description="Publish new datasets from configured Zenodo sources using local timestamp checkpoints."
    )
    parser.add_argument(
        "--sources-path",
        default=str(DEFAULT_SOURCES_PATH),
        help=f"Path to source query config JSON (default: {DEFAULT_SOURCES_PATH}).",
    )
    parser.add_argument(
        "--timestamp-path",
        default=str(DEFAULT_TIMESTAMP_PATH),
        help=f"Path to timestamp JSON (default: {DEFAULT_TIMESTAMP_PATH}).",
    )
    parser.add_argument(
        "--group-name",
        default=None,
        help="Databus group/account path (defaults to sources config defaults.group.name).",
    )
    parser.add_argument(
        "--group-title",
        default=None,
        help="Databus group title (defaults to sources config defaults.group.title).",
    )
    parser.add_argument(
        "--group-abstract",
        default=None,
        help="Databus group abstract (defaults to sources config defaults.group.abstract).",
    )
    parser.add_argument(
        "--group-description",
        default=None,
        help="Databus group description (defaults to sources config defaults.group.description).",
    )
    parser.add_argument(
        "--overlap-hours",
        type=int,
        default=24,
        help="Checkpoint overlap window to avoid missing late-indexed datasets.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="Zenodo /api/records page size for each source fetch.",
    )
    add_databus_publish_cli_args(parser)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Query sources and validate payload preparation without pushing to Databus.",
    )
    return parser


def main() -> int:
    """Iterate configured Zenodo sources, publish new datasets, update timestamps.

    Returns
    -------
    int
        Exit code ``0`` on success, ``1`` if a Databus POST fails.

    Raises
    ------
    SystemExit
        When API key is required but missing (non-dry-run).
    """
    load_dotenv_if_available()
    args = build_parser().parse_args()

    mode = "dry-run (no Databus POST)" if args.dry_run else "publish"
    print(f"[zenodo:sources] Starting ({mode}).", flush=True)
    print(f"[zenodo:sources] Sources config: {args.sources_path}", flush=True)
    print(f"[zenodo:sources] Timestamp state: {args.timestamp_path}", flush=True)
    print(
        f"[zenodo:sources] Requested page size: {args.page_size} (Zenodo may clamp).",
        flush=True,
    )

    config = load_source_config(path=Path(args.sources_path))
    sources = config["sources"]
    SOURCE_QUERY_PARAMS.clear()
    SOURCE_QUERY_PARAMS.update(sources)
    group_defaults = config["defaults"]["group"]

    timestamp_path = Path(args.timestamp_path)
    state = load_timestamp_state(path=timestamp_path)

    group = GroupMetadata(
        name=args.group_name or group_defaults["name"],
        title=args.group_title or group_defaults["title"],
        abstract=args.group_abstract or group_defaults["abstract"],
        description=args.group_description or group_defaults["description"],
    )
    mapper = ZenodoToDataBusMapper()
    print(f"[zenodo:sources] Zenodo API base: {mapper.zenodo_base_url}", flush=True)
    print(
        f"[zenodo:sources] Zenodo token: {'set (higher page limits)' if mapper.access_token else 'not set (anonymous)'}",
        flush=True,
    )
    print(f"[zenodo:sources] Databus group for payloads: {group.name!r}", flush=True)
    print(
        f"[zenodo:sources] Sources to run ({len(sources)}): {', '.join(sorted(sources))}",
        flush=True,
    )

    api_key = databus_api_key(args.api_key)
    if not args.dry_run and not api_key:
        raise SystemExit("Missing API key: pass --api-key or set DATABUS_API_KEY.")

    total_seen = 0
    total_new = 0
    total_published = 0
    for source_key in sources:
        print(f"[zenodo:sources] --- Source {source_key!r} ---", flush=True)
        records = mapper.fetch_source_records(source_key, page=1, size=args.page_size)
        total_seen += len(records)
        source_state = state.get(source_key) or {}
        new_hits = filter_new_datasets(records, source_state, overlap_hours=args.overlap_hours)
        total_new += len(new_hits)

        print(
            f"[zenodo:sources] source={source_key} seen={len(records)} new={len(new_hits)} "
            f"(overlap_hours={args.overlap_hours})",
            flush=True,
        )

        hits_to_process = [r for r in new_hits if str(r.get("id") or "").strip()]
        n_new = len(hits_to_process)
        if n_new:
            print(
                f"[zenodo:sources] Processing {n_new} dataset(s); each calls GET /api/records/<id> then builds payload.",
                flush=True,
            )
        for idx, rec in enumerate(hits_to_process, start=1):
            dataset_id = str(rec.get("id") or "").strip()
            print(
                f"[zenodo:sources] ({idx}/{n_new}) fetch + map Zenodo dataset id={dataset_id} …",
                flush=True,
            )
            payload = mapper.map_to_databus_dataset(dataset_id, group)
            if args.dry_run:
                print(
                    f"[zenodo:sources] ready: {payload.get('@id') or payload.get('version_id')}",
                    flush=True,
                )
                continue
            print(f"[zenodo:sources] ({idx}/{n_new}) POST Databus register …", flush=True)
            try:
                post_register_payload(
                    payload, api_key=api_key or "", register_url=args.register_url
                )
            except RuntimeError as err:
                print(
                    f"[zenodo:sources] publish failed for dataset {dataset_id}:",
                    flush=True,
                )
                print(str(err), flush=True)
                return 1
            source_state = advance_source_state(source_state, [rec])
            state[source_key] = source_state
            save_timestamp_state(state, path=timestamp_path)
            total_published += 1
            print(
                f"[zenodo:sources] published dataset {dataset_id}; checkpoint saved ({timestamp_path})",
                flush=True,
            )

    if args.dry_run:
        print(
            f"[zenodo:sources] dry-run done. seen={total_seen} new={total_new}",
            flush=True,
        )
        return 0

    print(
        f"[zenodo:sources] done. seen={total_seen} new={total_new} published={total_published} "
        f"timestamp_updated={timestamp_path}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
