from __future__ import annotations

from pathlib import Path

from databus_manager.scan_catalog import scan_catalog


def test_scan_catalog_discovers_single_entry(sample_catalog: Path) -> None:
    entries = scan_catalog(sample_catalog)
    assert len(entries) == 1
    e = entries[0]
    assert e.group_id.endswith("/wedowind/zenodo")
    assert e.artifact_id.endswith("/example-artefact-one")
    assert e.version_id.endswith("/v1.0.0")


def test_scan_catalog_skips_missing_artefact_metadata(sample_catalog: Path) -> None:
    artefact_file = sample_catalog / "group-zenodo" / "artefacts-1" / "artefact-metadata.jsonld"
    artefact_file.unlink()
    entries = scan_catalog(sample_catalog)
    assert entries == []
