from __future__ import annotations

import pytest

from databus_local_manager.parse import (
    build_prepare_metadata_parser,
    build_publish_local_catalog_parser,
)


def test_publish_local_parser_defaults() -> None:
    args = build_publish_local_catalog_parser().parse_args([])
    assert args.catalog == "catalog"
    assert args.publishings.endswith("catalog/logs/publishings.jsonl")
    assert args.api_key is None
    assert args.dry_run is False


def test_prepare_metadata_parser_requires_group_file() -> None:
    with pytest.raises(SystemExit):
        build_prepare_metadata_parser().parse_args([])


def test_prepare_metadata_parser_accepts_args() -> None:
    args = build_prepare_metadata_parser().parse_args(
        ["--group-file", "catalog/groups/zenodo.json"]
    )
    assert args.group_file == "catalog/groups/zenodo.json"
