from __future__ import annotations

import json
from pathlib import Path

from databus_local_manager.scan_catalog import scan_catalog


def test_scan_catalog_discovers_single_entry(sample_catalog: Path) -> None:
    groups = scan_catalog(sample_catalog)
    assert len(groups) == 1
    entry = groups[0]
    assert entry.path == sample_catalog / "groups" / "zenodo.json"
    assert entry.payload["group"]["id"].endswith("/wedowind/zenodo")


def test_scan_catalog_skips_non_object_json(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog"
    groups = catalog / "groups"
    groups.mkdir(parents=True)
    (groups / "bad.json").write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    assert scan_catalog(catalog) == []


def test_scan_catalog_empty_when_groups_dir_missing(tmp_path: Path) -> None:
    assert scan_catalog(tmp_path / "catalog") == []
