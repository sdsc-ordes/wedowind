from __future__ import annotations

import json
from pathlib import Path

import pytest

from databus_manager.compare_catalog_with_databus import compare_and_pull
from databus_manager.objects.metadata import ArtefactMetadata, GroupMetadata, VersionMetadata


def test_compare_and_pull_applies_remote_changes(
    sample_catalog: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get_remote(entry, _sparql_url):
        return (
            True,
            VersionMetadata(entry.version_id, "v1.0.0", "Version abstract", "Version description", "L", [{"downloadURL": "https://doi.org/10.1/x", "formatExtension": "zip", "compression": "none"}]),
            GroupMetadata(entry.group_id, "Remote group title", "Group abstract", "Group description"),
            ArtefactMetadata(entry.artifact_id, "Artefact one", "Artefact abstract", "Artefact description"),
        )

    monkeypatch.setattr("databus_manager.compare_catalog_with_databus.get_remote", fake_get_remote)
    results, scanned_refs = compare_and_pull(sample_catalog, sparql_url="https://example.org/sparql", apply_changes=True)
    assert len(results) == 1
    assert len(scanned_refs) == 1
    assert results[0]["group_mismatch"] is True
    assert results[0]["changed_local_from_remote"] is True

    group_file = sample_catalog / "group-zenodo" / "group-metadata.jsonld"
    group_doc = json.loads(group_file.read_text(encoding="utf-8"))
    assert group_doc["@graph"][0]["title"] == "Remote group title"
