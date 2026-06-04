"""CLI: push OEMetadata for one Zenodo record to OEP."""

from __future__ import annotations

import argparse
from pathlib import Path

from omi.base import MetadataError

from mappers.checkpoint_state import advance_source_state
from mappers.load_env import load_dotenv_if_available
from mappers.oep.api import oep_api_token, publish_to_oep, validate_oemetadata
from mappers.oep.oep_defaults import apply_oep_cli_overrides, parse_oep_defaults
from mappers.oep.oep_table import OepTableProvisionError
from mappers.oep.utils import add_oep_publish_cli_args
from mappers.zenodo.manage_sources import (
    DEFAULT_SOURCES_PATH,
    DEFAULT_TIMESTAMP_PATH,
    load_source_config,
    load_source_query_params,
    load_timestamp_state,
    save_timestamp_state,
)
from mappers.zenodo.oep_mapper import ZenodoToOepMapper


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for single-record Zenodo publish.

    Returns
    -------
    argparse.ArgumentParser
        Parser with dataset, source, OEP, and dry-run options.
    """
    parser = argparse.ArgumentParser(description="Map one Zenodo record to OEMetadata and publish to OEP.")
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--sources-path", default=str(DEFAULT_SOURCES_PATH))
    parser.add_argument("--source-key", default=None)
    parser.add_argument("--timestamp-path", default=str(DEFAULT_TIMESTAMP_PATH))
    add_oep_publish_cli_args(parser)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _resolve_source_key(sources_path: Path, requested: str | None) -> str:
    """Resolve ``--source-key`` against configured Zenodo sources.

    Parameters
    ----------
    sources_path : pathlib.Path
        Path to the Zenodo sources JSON config.
    requested : str or None
        CLI ``--source-key`` value; may be ``None``.

    Returns
    -------
    str
        Resolved source key present in the config.

    Raises
    ------
    SystemExit
        When no sources exist, multiple sources require an explicit key, or
        the requested key is unknown.
    """
    params = load_source_query_params(path=sources_path)
    keys = sorted(params.keys())
    if not keys:
        raise SystemExit(f"No sources defined in {sources_path}")
    if requested is None:
        if len(keys) == 1:
            return keys[0]
        raise SystemExit(f"--source-key required; sources: {keys}")
    if requested not in params:
        raise SystemExit(f"Unknown --source-key {requested!r}; valid: {keys}")
    return requested


def main() -> int:
    """Map one Zenodo record and publish OEMetadata to OEP.

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
    source_key = _resolve_source_key(Path(args.sources_path), args.source_key)
    config = load_source_config(path=Path(args.sources_path))
    oep_defaults = apply_oep_cli_overrides(
        parse_oep_defaults(config.get("defaults", {}).get("oep"), provenance_label="zenodo"),
        args,
    )

    mapper = ZenodoToOepMapper(source_key=source_key)
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
        print(f"[zenodo:oep] publish failed: {err}")
        return 1

    state_path = Path(args.timestamp_path)
    state = load_timestamp_state(path=state_path)
    source_state = state.get(source_key) or {}
    record = mapper.client.get_record(args.dataset_id)
    state[source_key] = advance_source_state(source_state, processed_datasets=[record])
    save_timestamp_state(state, path=state_path, enabled=not args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
