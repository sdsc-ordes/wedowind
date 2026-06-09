from __future__ import annotations

import json
from pathlib import Path

import pytest

from databus_local_manager import prepare_metadata as mod
from databus_local_manager.scan_catalog import CatalogGroupFile


def test_prepare_group_versions_builds_dataset_payload(
    sample_catalog: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    group_file = sample_catalog / "groups" / "zenodo.json"
    payload = json.loads(group_file.read_text(encoding="utf-8"))

    monkeypatch.setattr(
        mod,
        "create_distribution",
        lambda **kwargs: {"downloadURL": kwargs["url"], "cvs": kwargs["cvs"]},
    )

    def fake_create_dataset(**kwargs):
        return {"@id": kwargs["version_id"], "distribution": kwargs["distributions"]}

    monkeypatch.setattr(mod, "create_dataset", fake_create_dataset)
    prepared = mod.prepare_group_versions(CatalogGroupFile(path=group_file, payload=payload))

    assert len(prepared) == 1
    assert prepared[0].version_id.endswith("/v1.0.0")
    assert prepared[0].dataset_payload["@id"].endswith("/v1.0.0")
    assert prepared[0].group_title
    assert prepared[0].version_title
