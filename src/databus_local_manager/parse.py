"""CLI ``argparse`` builders for local catalog publish flow."""

from __future__ import annotations

import argparse


def build_publish_local_catalog_parser() -> argparse.ArgumentParser:
    """CLI for scan + publish (local catalog root and publishings log)."""
    from databus_local_manager.publish_local_catalog import DEFAULT_REGISTER_URL

    parser = argparse.ArgumentParser(
        description="Scan local catalog JSON, prepare metadata, and publish new versions."
    )
    parser.add_argument("--catalog", default="catalog", help="Catalog root directory.")
    parser.add_argument(
        "--publishings",
        default="catalog/logs/publishings.jsonl",
        help="Append-only publishings JSONL (schema: publishing.schema.json).",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Databus API key. If omitted, DATABUS_API_KEY env var is used.",
    )
    parser.add_argument(
        "--register-url",
        default=DEFAULT_REGISTER_URL,
        help="Register endpoint URL for publish.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Do not publish or append publishings."
    )
    return parser


def build_prepare_metadata_parser() -> argparse.ArgumentParser:
    """CLI to validate one group file and print prepared payloads only."""
    parser = argparse.ArgumentParser(
        description="Validate group catalog JSON and prepare metadata payloads without publishing."
    )
    parser.add_argument(
        "--group-file",
        required=True,
        help="Path to a group catalog JSON file (e.g. catalog/groups/zenodo.json).",
    )
    return parser


def build_sync_catalog_parser() -> argparse.ArgumentParser:
    """Backward-compatible alias for old CLI name."""
    return build_publish_local_catalog_parser()


def build_publish_group_parser() -> argparse.ArgumentParser:
    """Backward-compatible alias for old CLI name."""
    return build_prepare_metadata_parser()
