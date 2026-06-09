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

    import mappers.ckan.mapper as ckan_mapper_mod

    class FakeRemoteCKAN:
        def __init__(self, url: str):
            self.url = url

    monkeypatch.setattr(ckan_mapper_mod, "RemoteCKAN", FakeRemoteCKAN)

    import mappers.ckan.publish_sources as ps

    cfg = {
        "sources": {
            "test-source": {
                "group": {
                    "name": "wedowind/test",
                    "title": "T",
                    "abstract": "A",
                    "description": "D",
                },
                "api": {"base_url": "https://example.org"},
                "queries": [
                    {
                        "id": "src-one",
                        "package_search": {"fq": "groups:test", "rows": 10},
                    }
                ],
            }
        }
    }
    monkeypatch.setattr(ps, "load_ckan_sources", lambda path: cfg)
    monkeypatch.setattr(
        ps,
        "load_ckan_timestamp_state",
        lambda path, **_kwargs: {
            "sources": {
                "test-source": {
                    "queries": {
                        "src-one": {
                            "last_run_at": None,
                            "last_seen_updated": None,
                            "last_seen_dataset_id": None,
                            "processed_dataset_ids": [],
                        }
                    }
                }
            }
        },
    )

    hits = [
        {"name": "dataset-one", "metadata_modified": "2026-05-01T12:00:00.000000"},
    ]
    monkeypatch.setattr(ps, "iter_package_search_results", lambda _ckan, _params: iter(hits))

    monkeypatch.setattr(
        ps.CKANToDataBusMapper,
        "map_to_databus_dataset",
        lambda self, dataset_id, group: {"@id": f"urn:test:{dataset_id}"},
    )

    monkeypatch.setattr(sys, "argv", ["publish_sources", "--dry-run"])
    assert ps.main() == 0
