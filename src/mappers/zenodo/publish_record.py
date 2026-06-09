"""CLI: publish one Zenodo dataset and advance one source checkpoint."""

from __future__ import annotations

import argparse
from pathlib import Path

from databus_local_manager.load_env import load_dotenv_if_available
from mappers.checkpoint_state import advance_source_state
from mappers.databus import databus_api_key, post_register_payload
from mappers.utils import GroupMetadata, add_databus_publish_cli_args
from mappers.zenodo.manage_sources import (
    DEFAULT_SOURCES_PATH,
    DEFAULT_TIMESTAMP_PATH,
    load_source_query_params,
    load_timestamp_state,
    save_timestamp_state,
)
from mappers.zenodo.mapper import ZenodoToDataBusMapper


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for ``python -m mappers.zenodo.publish_record``.

    Returns
    -------
    argparse.ArgumentParser
        Parser with dataset, group, Databus, source/timestamp, and dry-run options.
    """
    parser = argparse.ArgumentParser(
        description="Publish one Zenodo dataset to Databus via mapper."
    )
    parser.add_argument(
        "--dataset-id",
        required=True,
        help="Dataset id (numeric Zenodo id; Zenodo API path is /api/records/{id}).",
    )
    parser.add_argument(
        "--group-name", required=True, help="Databus group slug used in identifier."
    )
    parser.add_argument("--group-title", required=True, help="Databus group title.")
    parser.add_argument("--group-abstract", required=True, help="Databus group abstract.")
    parser.add_argument("--group-description", required=True, help="Databus group description.")
    add_databus_publish_cli_args(parser)
    parser.add_argument(
        "--sources-path",
        default=str(DEFAULT_SOURCES_PATH),
        help=f"Zenodo sources JSON (defines valid --source-key values; default: {DEFAULT_SOURCES_PATH}).",
    )
    parser.add_argument(
        "--source-key",
        default=None,
        help="Timestamp source key to advance after publish (defaults to the only source if config has one).",
    )
    parser.add_argument(
        "--timestamp-path",
        default=str(DEFAULT_TIMESTAMP_PATH),
        help=f"Path to timestamp JSON (default: {DEFAULT_TIMESTAMP_PATH}).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Build payload only, do not POST.")
    return parser


def _resolve_source_key(sources_path: Path, requested: str | None) -> str:
    """Resolve ``--source-key`` against Zenodo ``sources.json``.

    Parameters
    ----------
    sources_path : pathlib.Path
        Path to sources JSON.
    requested : str or None
        Explicit ``--source-key``, or ``None`` to pick the sole source when only one exists.

    Returns
    -------
    str
        Valid source key.

    Raises
    ------
    SystemExit
        If no sources exist, multiple sources require an explicit key, or key is unknown.
    """
    params = load_source_query_params(path=sources_path)
    keys = sorted(params.keys())
    if not keys:
        raise SystemExit(f"No sources defined in {sources_path}")
    if requested is None:
        if len(keys) == 1:
            return keys[0]
        raise SystemExit(
            f"--source-key is required when multiple sources exist in {sources_path}: {keys}"
        )
    if requested not in params:
        raise SystemExit(
            f"Unknown --source-key {requested!r}; valid keys from {sources_path}: {keys}"
        )
    return requested


def main() -> int:
    """Run publish: map dataset, optionally POST to Databus, advance checkpoint.

    Returns
    -------
    int
        Process exit code (``0`` success, ``1`` publish failure).

    Raises
    ------
    SystemExit
        Missing API key when not dry-run; invalid ``--source-key``.
    """
    load_dotenv_if_available()
    args = build_parser().parse_args()
    args.source_key = _resolve_source_key(Path(args.sources_path), args.source_key)
    mapper = ZenodoToDataBusMapper()
    group = GroupMetadata(
        name=args.group_name,
        title=args.group_title,
        abstract=args.group_abstract,
        description=args.group_description,
    )
    payload = mapper.map_to_databus_dataset(args.dataset_id, group)
    print(f"[mapper:zenodo] prepared version: {payload.get('@id') or payload.get('version_id')}")
    if args.dry_run:
        print("[mapper:zenodo] dry-run enabled; skipping publish.")
        return 0

    api_key = databus_api_key(args.api_key)
    if not api_key:
        raise SystemExit("Missing API key: pass --api-key or set DATABUS_API_KEY.")
    try:
        post_register_payload(payload, api_key=api_key, register_url=args.register_url)
    except RuntimeError as err:
        print("[mapper:zenodo] publish failed:")
        print(str(err))
        return 1
    state_path = Path(args.timestamp_path)
    state = load_timestamp_state(path=state_path)
    source_state = state.get(args.source_key) or {}
    zenodo_record = mapper._get_record(args.dataset_id)
    state[args.source_key] = advance_source_state(source_state, processed_datasets=[zenodo_record])
    save_timestamp_state(state, path=state_path)
    print(f"[mapper:zenodo] updated timestamp state: {state_path}")
    print("[mapper:zenodo] published successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
