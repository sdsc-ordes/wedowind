from __future__ import annotations

import json
from pathlib import Path

import pytest

from databus_manager import sync_catalog_with_databus as mod
from databus_manager.scan_catalog import scan_catalog


def test_sync_main_appends_logs_and_publishings(
    sample_catalog: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    discrepancy_file = tmp_path / "discrepancies.jsonl"
    publishings_file = tmp_path / "publishings.jsonl"
    published: list[Path] = []

    version_path = sample_catalog / "group-zenodo" / "artifact-example-artefact-one" / "version-1" / "version.jsonld"

    monkeypatch.setattr(
        "sys.argv",
        [
            "sync",
            "--catalog",
            str(sample_catalog),
            "--publishings",
            str(publishings_file),
            "--discrepancy-log",
            str(discrepancy_file),
            "--api-key",
            "token",
            "--register-url",
            "https://example.org/register",
        ],
    )
    monkeypatch.setattr(
        mod,
        "compare_and_pull",
        lambda *args, **kwargs: (
            [
                {
                    "version_id": "https://databus.openenergyplatform.org/wedowind/zenodo/example-artefact-one/v1.0.0",
                    "group_id": "https://databus.openenergyplatform.org/wedowind/zenodo",
                    "artifact_id": "https://databus.openenergyplatform.org/wedowind/zenodo/example-artefact-one",
                    "version_file": str(version_path),
                    "group_file": str(sample_catalog / "group-zenodo" / "group-metadata.jsonld"),
                    "artifact_file": str(
                        sample_catalog / "group-zenodo" / "artifact-example-artefact-one" / "artefact-metadata.jsonld"
                    ),
                    "remote_version_exists": False,
                    "remote_group_exists": False,
                    "remote_artefact_exists": False,
                    "version_mismatch": False,
                    "group_mismatch": False,
                    "artefact_mismatch": False,
                    "changed_local_from_remote": False,
                    "discrepancy_entries": [
                        {
                            "timestamp": "2026-01-01T00:00:00+00:00",
                            "entity_id": "x",
                            "entity_type": "group",
                            "metadata_field": "title",
                            "remote_value": "r",
                            "local_value": "l",
                        }
                    ],
                }
            ],
            scan_catalog(sample_catalog),
        ),
    )
    monkeypatch.setattr(mod, "sparql_remote_version_exists", lambda *_: False)
    monkeypatch.setattr(mod, "publish", lambda version_file, api_key, register_url: published.append(version_file))
    monkeypatch.setattr(mod, "utc_now_iso", lambda: "2026-01-01T00:00:00+00:00")

    rc = mod.main()
    assert rc == 0
    assert published == [version_path]

    discrepancy_rows = discrepancy_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(discrepancy_rows) == 1

    publishings_rows = [json.loads(line) for line in publishings_file.read_text(encoding="utf-8").splitlines() if line]
    assert len(publishings_rows) == 1
    assert publishings_rows[0]["entity_id"].endswith("/v1.0.0")
