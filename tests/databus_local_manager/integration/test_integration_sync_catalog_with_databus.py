from __future__ import annotations

import json
from pathlib import Path

import pytest

from databus_local_manager import publish_local_catalog as mod
from databus_local_manager.prepare_metadata import PreparedVersion


def test_publish_local_main_appends_publishings(
    sample_catalog: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    publishings_file = tmp_path / "publishings.jsonl"
    posted: list[str] = []
    version_id = (
        "https://databus.openenergyplatform.org/wedowind/zenodo/example-artifact-one/v1.0.0"
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "publish_local",
            "--catalog",
            str(sample_catalog),
            "--publishings",
            str(publishings_file),
            "--api-key",
            "token",
            "--register-url",
            "https://example.org/register",
        ],
    )
    monkeypatch.setattr(
        mod,
        "_scan_prepared_versions",
        lambda *_: [
            PreparedVersion(
                source_file=sample_catalog / "groups" / "zenodo.json",
                group_id="https://databus.openenergyplatform.org/wedowind/zenodo",
                group_title="Zenodo",
                artifact_id="https://databus.openenergyplatform.org/wedowind/zenodo/example-artifact-one",
                version_id=version_id,
                version_title="Example dataset",
                dataset_payload={"@id": version_id},
            )
        ],
    )
    monkeypatch.setattr(
        mod,
        "_register_payload",
        lambda dataset_payload, **kwargs: posted.append(str(dataset_payload["@id"])),
    )
    monkeypatch.setattr(mod, "utc_now_iso", lambda: "2026-01-01T00:00:00+00:00")

    rc = mod.main()
    assert rc == 0
    assert posted == [version_id]

    publishings_rows = [
        json.loads(line)
        for line in publishings_file.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert len(publishings_rows) == 1
    assert publishings_rows[0]["entity_id"].endswith("/v1.0.0")
