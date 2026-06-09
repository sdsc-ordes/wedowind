from __future__ import annotations

from pathlib import Path

import pytest

from databus_local_manager.logs import PublishingEntry
from databus_local_manager.publish_local_catalog import _scan_prepared_versions


def test_scan_prepared_versions_works_for_sample_catalog(
    sample_catalog: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "databus_local_manager.prepare_metadata.create_distribution",
        lambda **kwargs: "dist",
    )
    monkeypatch.setattr(
        "databus_local_manager.prepare_metadata.create_dataset",
        lambda **kwargs: {
            "@id": kwargs["version_id"],
            "distribution": kwargs["distributions"],
        },
    )
    versions = _scan_prepared_versions(sample_catalog)
    assert len(versions) == 1
    assert versions[0].version_id.endswith("/v1.0.0")


def test_publishing_entry_accepts_version_entity_only() -> None:
    row = PublishingEntry(
        timestamp="2026-01-01T00:00:00+00:00", entity_id="v1", entity_type="version"
    )
    assert row.entity_type == "version"
