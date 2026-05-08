"""Publish datasets discovered via configured CKAN ``package_search`` queries."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from databus_local_manager.load_env import load_dotenv_if_available
from mappers.checkpoint_state import (
    advance_source_state,
    filter_new_datasets,
    canonical_checkpoint,
)
from mappers.ckan.manage_sources import (
    DEFAULT_SOURCES_PATH,
    DEFAULT_TIMESTAMP_PATH,
    load_ckan_sources,
    load_ckan_timestamp_state,
    save_ckan_timestamp_state,
)
from mappers.ckan.mapper import CKANToDataBusMapper, iter_package_search_results
from mappers.databus import databus_api_key, post_register_payload
from mappers.utils import GroupMetadata, add_databus_publish_cli_args


def _payload_summary(payload: Any) -> str:
    """Extract a short identifier string from a Databus registration payload.

    Parameters
    ----------
    payload : Any
        Dict-shaped JSON-LD or other (fallback string preview).

    Returns
    -------
    str
        ``@id`` / ``version_id`` or graph node id when present; else a truncated summary.
    """
    if not isinstance(payload, dict):
        return str(payload)[:300]
    for key in ("@id", "version_id"):
        val = payload.get(key)
        if val:
            return str(val)
    graph = payload.get("@graph")
    if isinstance(graph, list):
        for node in graph:
            if isinstance(node, dict):
                vid = node.get("@id") or node.get("version_id")
                if vid:
                    return str(vid)
    keys = sorted(payload.keys())
    return f"(no top-level @id; keys={keys[:15]})"


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for ``python -m mappers.ckan.publish_sources``.

    Returns
    -------
    argparse.ArgumentParser
        Parser with sources/timestamp paths, optional source filter, overlap, Databus args.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Publish datasets from configured CKAN sources (package_search), "
            "using local timestamp checkpoints."
        )
    )
    parser.add_argument(
        "--sources-path",
        default=str(DEFAULT_SOURCES_PATH),
        help=f"Path to CKAN sources JSON (default: {DEFAULT_SOURCES_PATH}).",
    )
    parser.add_argument(
        "--timestamp-path",
        default=str(DEFAULT_TIMESTAMP_PATH),
        help=f"Path to CKAN timestamp JSON (default: {DEFAULT_TIMESTAMP_PATH}).",
    )
    parser.add_argument(
        "--source-id",
        default=None,
        help="Run only this top-level source id from the registry (default: all sources).",
    )
    parser.add_argument(
        "--overlap-hours",
        type=int,
        default=24,
        help="Checkpoint overlap window to avoid missing late-indexed datasets.",
    )
    add_databus_publish_cli_args(parser)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Query CKAN and validate payload preparation without pushing to Databus.",
    )
    return parser


def main() -> int:
    """Run configured ``package_search`` queries, publish, and update checkpoints.

    Returns
    -------
    int
        ``0`` on success, ``1`` if any Databus POST fails.

    Raises
    ------
    SystemExit
        When API key is required but missing, or ``--source-id`` is unknown.
    """
    load_dotenv_if_available()
    args = build_parser().parse_args()

    sources_path = Path(args.sources_path).expanduser().resolve()
    timestamp_path = Path(args.timestamp_path).expanduser().resolve()

    mode = "dry-run (no Databus POST)" if args.dry_run else "publish"
    print(f"[ckan:sources] Starting ({mode}).", flush=True)
    print(f"[ckan:sources] Sources config (resolved): {sources_path}", flush=True)
    print(f"[ckan:sources] Timestamp state (resolved): {timestamp_path}", flush=True)
    print(f"[ckan:sources] overlap_hours={args.overlap_hours}", flush=True)
    if args.source_id is not None:
        print(f"[ckan:sources] Source filter: {args.source_id!r}", flush=True)

    cfg = load_ckan_sources(path=sources_path)
    sources = cfg.get("sources") or {}
    if not isinstance(sources, dict) or not sources:
        raise SystemExit("No CKAN sources configured.")

    state = load_ckan_timestamp_state(
        path=timestamp_path,
        sources_path=sources_path,
    )

    api_key = databus_api_key(args.api_key)
    if not args.dry_run and not api_key:
        raise SystemExit("Missing API key: pass --api-key or set DATABUS_API_KEY.")

    total_seen = 0
    total_new = 0
    total_published = 0

    source_items = sorted(sources.items())
    if args.source_id is not None:
        sid = str(args.source_id).strip()
        if sid not in sources:
            raise SystemExit(f"Unknown source id: {sid!r}")
        source_items = [(sid, sources[sid])]

    print(
        f"[ckan:sources] Sources to run ({len(source_items)}): "
        f"{', '.join(s for s, _ in source_items)}",
        flush=True,
    )

    for source_id, entry in source_items:
        if not isinstance(entry, dict):
            continue
        api_cfg = entry.get("api") or {}
        base_url = str(api_cfg.get("base_url") or "").strip()
        if not base_url:
            print(
                f"[ckan:sources] skip source={source_id}: missing api.base_url",
                flush=True,
            )
            continue

        group_cfg = entry.get("group") or {}
        group = GroupMetadata(
            name=str(group_cfg.get("name") or ""),
            title=str(group_cfg.get("title") or ""),
            abstract=str(group_cfg.get("abstract") or ""),
            description=str(group_cfg.get("description") or ""),
        )
        mapper = CKANToDataBusMapper(base_url)
        print(
            f"[ckan:sources] --- source={source_id} CKAN base={base_url!r} "
            f"group={group.name!r} ---",
            flush=True,
        )

        queries_list = entry.get("queries") or []
        if not isinstance(queries_list, list):
            continue

        for query in queries_list:
            if not isinstance(query, dict):
                continue
            query_id = query.get("id")
            if not isinstance(query_id, str) or not query_id.strip():
                continue

            search_params = query.get("package_search")
            if not isinstance(search_params, dict) or not search_params:
                print(
                    f"[ckan:sources] skip source={source_id} query={query_id}: "
                    "no package_search params (see src/mappers/ckan/config/sources.json).",
                    flush=True,
                )
                continue

            fq_preview = str(search_params.get("fq") or "")[:100]
            print(
                f"[ckan:sources] Querying CKAN package_search for query={query_id!r} "
                f"(may paginate; fq starts {fq_preview!r}…)",
                flush=True,
            )
            pkgs: list[dict[str, Any]] = list(
                iter_package_search_results(mapper.ckan, search_params)
            )
            total_seen += len(pkgs)

            records = [
                {
                    "id": str(p.get("name") or ""),
                    "updated": str(p.get("metadata_modified") or ""),
                }
                for p in pkgs
                if isinstance(p, dict) and p.get("name")
            ]

            sources_top = state.setdefault("sources", {})
            src_block = sources_top.setdefault(source_id, {"queries": {}})
            queries_map = src_block.setdefault("queries", {})
            raw_query_state = canonical_checkpoint(queries_map.get(query_id))
            queries_map[query_id] = raw_query_state

            new_entries = filter_new_datasets(
                records, raw_query_state, overlap_hours=args.overlap_hours
            )
            total_new += len(new_entries)

            print(
                f"[ckan:sources] source={source_id} query={query_id} "
                f"seen={len(records)} new={len(new_entries)} (overlap_hours={args.overlap_hours})",
                flush=True,
            )

            records_to_process = [r for r in new_entries if str(r.get("id") or "").strip()]
            n_new = len(records_to_process)
            if n_new:
                print(
                    f"[ckan:sources] Processing {n_new} dataset(s); each calls package_show then builds payload.",
                    flush=True,
                )

            for idx, rec in enumerate(records_to_process, start=1):
                dataset_id = str(rec.get("id") or "").strip()
                if not dataset_id:
                    continue
                print(
                    f"[ckan:sources] ({idx}/{n_new}) package_show + map dataset name={dataset_id!r} …",
                    flush=True,
                )
                payload = mapper.map_to_databus_dataset(dataset_id, group)
                if args.dry_run:
                    print(
                        f"[ckan:sources] ready: {_payload_summary(payload)}",
                        flush=True,
                    )
                    continue
                print(
                    f"[ckan:sources] ({idx}/{n_new}) POST Databus register …",
                    flush=True,
                )
                try:
                    post_register_payload(
                        payload, api_key=api_key or "", register_url=args.register_url
                    )
                except RuntimeError as err:
                    print(
                        f"[ckan:sources] publish failed for dataset {dataset_id}:",
                        flush=True,
                    )
                    print(str(err), flush=True)
                    return 1
                pkg = getattr(mapper, "_last_ckan_package", None) or {}
                checkpoint_rec = {
                    "id": dataset_id,
                    "updated": str(pkg.get("metadata_modified") or rec.get("updated") or ""),
                }
                raw_query_state = advance_source_state(
                    raw_query_state,
                    [checkpoint_rec],
                    run_at=datetime.now(UTC),
                )
                queries_map[query_id] = raw_query_state
                save_ckan_timestamp_state(state, path=timestamp_path)
                total_published += 1
                print(
                    f"[ckan:sources] published dataset {dataset_id}; checkpoint saved ({timestamp_path})",
                    flush=True,
                )

    if args.dry_run:
        print(
            f"[ckan:sources] dry-run done. seen={total_seen} new={total_new}",
            flush=True,
        )
        return 0

    print(
        f"[ckan:sources] done. seen={total_seen} new={total_new} published={total_published} "
        f"timestamp_updated={timestamp_path}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
