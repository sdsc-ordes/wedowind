from __future__ import annotations

import json
from pathlib import Path

from databus_manager.objects.metadata import ArtefactMetadata, GroupMetadata, VersionMetadata


def test_group_discrepancies_vs() -> None:
    local = GroupMetadata("g", "A", "B", "C")
    remote = GroupMetadata("g", "A", "B2", "C")
    rows = local.discrepancies_vs(remote, timestamp="2026-01-01T00:00:00+00:00")
    assert len(rows) == 1
    assert rows[0].entity_type == "group"
    assert rows[0].metadata_field == "abstract"


def test_artifact_discrepancies_vs() -> None:
    local = ArtefactMetadata("a", "T1", "A1", "D1")
    remote = ArtefactMetadata("a", "T2", "A1", "D1")
    rows = local.discrepancies_vs(remote, timestamp="2026-01-01T00:00:00+00:00")
    assert len(rows) == 1
    assert rows[0].entity_type == "artifact"
    assert rows[0].metadata_field == "title"


def test_version_normalization_and_distribution_discrepancy() -> None:
    local = VersionMetadata(
        "v",
        "t",
        "a",
        "d",
        "l",
        [
            {"downloadURL": "u2", "formatExtension": "zip", "compression": "none"},
            {"downloadURL": "u1", "formatExtension": "txt", "compression": "none"},
        ],
    )
    remote = VersionMetadata(
        "v",
        "t",
        "a",
        "d",
        "l",
        [{"downloadURL": "u1", "formatExtension": "txt", "compression": "none"}],
    )
    assert local.equals_normalized(remote) is False
    rows = local.discrepancies_vs(remote, timestamp="2026-01-01T00:00:00+00:00")
    assert any(r.metadata_field == "distribution" for r in rows)


def test_write_remote_to_file_for_group(tmp_path: Path) -> None:
    path = tmp_path / "group-metadata.jsonld"
    path.write_text(
        json.dumps(
            {
                "@context": "x",
                "@graph": [{"@id": "g", "@type": "Group", "title": "old", "abstract": "a", "description": "d"}],
            }
        ),
        encoding="utf-8",
    )
    GroupMetadata.write_remote_to_file(path, GroupMetadata("g", "new", "a2", "d2"))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["@graph"][0]["title"] == "new"
    assert data["@graph"][0]["abstract"] == "a2"
