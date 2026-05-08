from __future__ import annotations

import sys

import pytest


def test_publish_sources_dry_run(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    fake_databusclient = __import__("types").SimpleNamespace(
        create_distribution=lambda **kwargs: kwargs,
        create_dataset=lambda version_id, **kwargs: {"@id": version_id, **kwargs},
        run=lambda *args, **kwargs: None,
    )
    monkeypatch.setitem(sys.modules, "databusclient", fake_databusclient)

    import mappers.zenodo.publish_sources as ps

    cfg = {
        "defaults": {
            "group": {
                "name": "wedowind/zenodo",
                "title": "Group title",
                "abstract": "Group abstract",
                "description": "Group description",
            }
        },
        "sources": {"test_source": {"communities": "wedowind"}},
    }
    monkeypatch.setattr(ps, "load_source_config", lambda path: cfg)
    monkeypatch.setattr(
        ps,
        "load_timestamp_state",
        lambda path: {
            "test_source": {
                "processed_dataset_ids": [],
                "last_seen_updated": None,
            }
        },
    )

    monkeypatch.setattr(
        ps.ZenodoToDataBusMapper,
        "fetch_source_records",
        lambda self, source_key, page=1, size=100: [
            {"id": "1001", "updated": "2026-05-08T12:00:00+00:00"},
        ],
    )
    monkeypatch.setattr(
        ps.ZenodoToDataBusMapper,
        "map_to_databus_dataset",
        lambda self, dataset_id, group: {
            "@id": "https://databus.example.org/wedowind/zenodo/ex/v1.0.0"
        },
    )

    import mappers.zenodo.manage_sources as zms

    saved_sources = dict(zms.SOURCE_QUERY_PARAMS)
    try:
        monkeypatch.setattr(sys, "argv", ["publish_sources", "--dry-run"])
        assert ps.main() == 0
    finally:
        zms.SOURCE_QUERY_PARAMS.clear()
        zms.SOURCE_QUERY_PARAMS.update(saved_sources)
