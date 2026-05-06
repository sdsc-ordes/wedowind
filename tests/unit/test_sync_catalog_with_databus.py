from __future__ import annotations

from pathlib import Path

import pytest

from databus_manager.objects.metadata import CatalogVersionRef
from databus_manager.objects.logs import PublishingLedgerEntry
from databus_manager.sync_catalog_with_databus import classify_entries


def test_classify_entries_states(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    entries = [
        CatalogVersionRef(tmp_path / "v1.jsonld", tmp_path / "g1.jsonld", tmp_path / "a1.jsonld", "v1", "g1", "a1"),
        CatalogVersionRef(tmp_path / "v2.jsonld", tmp_path / "g2.jsonld", tmp_path / "a2.jsonld", "v2", "g2", "a2"),
        CatalogVersionRef(tmp_path / "v3.jsonld", tmp_path / "g3.jsonld", tmp_path / "a3.jsonld", "v3", "g3", "a3"),
    ]

    monkeypatch.setattr("databus_manager.sync_catalog_with_databus.scan_catalog", lambda _: entries)
    monkeypatch.setattr(
        "databus_manager.sync_catalog_with_databus.sparql_remote_version_exists",
        lambda version_id, _sparql_url: version_id in {"v1", "v2"},
    )

    ledger = {
        "v1": PublishingLedgerEntry(
            timestamp="2026-01-01T00:00:00+00:00", entity_id="v1", entity_type="version"
        )
    }
    rows = classify_entries(tmp_path, ledger_map=ledger, sparql_url="https://example.org/sparql")
    status = {r["version_id"]: r["status"] for r in rows}
    assert status == {"v1": "published", "v2": "ledger_mismatch", "v3": "new"}
