from __future__ import annotations

import pytest

from databus_manager.parse import build_publish_group_parser, build_sync_catalog_parser


def test_sync_parser_defaults() -> None:
    args = build_sync_catalog_parser().parse_args([])
    assert args.catalog == "catalog"
    assert args.ledger.endswith("catalog/.databus/publish_ledger.jsonl")
    assert args.discrepancy_log.endswith("catalog/.databus/discrepancies.jsonl")
    assert args.api_key is None
    assert args.dry_run is False
    assert args.pull_only is False


def test_publish_parser_requires_version_file() -> None:
    with pytest.raises(SystemExit):
        build_publish_group_parser().parse_args([])


def test_publish_parser_accepts_args() -> None:
    args = build_publish_group_parser().parse_args(["--version-file", "catalog/x/version.jsonld"])
    assert args.version_file == "catalog/x/version.jsonld"
    assert args.api_key is None
