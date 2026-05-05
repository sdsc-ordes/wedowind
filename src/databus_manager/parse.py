"""CLI ``argparse`` builders for sync and publish entrypoints."""

from __future__ import annotations

import argparse

from databus_manager.sparql import SPARQL_URL_DEFAULT


def build_sync_catalog_parser() -> argparse.ArgumentParser:
    from databus_manager.publish_group_metadata import DEFAULT_REGISTER_URL

    parser = argparse.ArgumentParser(description="Sync catalog with Databus before publish.")
    parser.add_argument("--catalog", default="catalog", help="Catalog root directory.")
    parser.add_argument(
        "--ledger",
        default="catalog/.databus/publish_ledger.jsonl",
        help="Local publish ledger JSONL (schema: publishing.schema.json).",
    )
    parser.add_argument(
        "--discrepancy-log",
        default="catalog/.databus/discrepancies.jsonl",
        help="Append field-level discrepancy records JSONL (schema: discrepancy.schema.json).",
    )
    parser.add_argument("--sparql-url", default=SPARQL_URL_DEFAULT, help="SPARQL endpoint URL.")
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
    parser.add_argument("--dry-run", action="store_true", help="Do not modify catalog or publish.")
    parser.add_argument(
        "--pull-only",
        action="store_true",
        help="Compare/pull only; do not publish new entries.",
    )
    return parser


def build_publish_group_parser() -> argparse.ArgumentParser:
    """CLI for publishing a single catalog version with group metadata (see ``publish_group_metadata``)."""

    from databus_manager.publish_group_metadata import DEFAULT_REGISTER_URL

    parser = argparse.ArgumentParser(description="Publish one version with group metadata.")
    parser.add_argument(
        "--version-file",
        required=True,
        help="Path to catalog version JSON-LD file (e.g. catalog/.../version.jsonld).",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Databus API key. If omitted, DATABUS_API_KEY env var is used.",
    )
    parser.add_argument(
        "--register-url",
        default=DEFAULT_REGISTER_URL,
        help=f"Register endpoint (default: {DEFAULT_REGISTER_URL}).",
    )
    return parser
