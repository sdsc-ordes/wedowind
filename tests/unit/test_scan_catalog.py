from __future__ import annotations

import shutil
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
    artefact_file = (
        sample_catalog / "group-zenodo" / "artifact-example-artefact-one" / "artefact-metadata.jsonld"
    )
    artefact_file.unlink()
    entries = scan_catalog(sample_catalog)
    assert entries == []


def test_scan_catalog_discovers_v_prefixed_version_folder(sample_catalog: Path) -> None:
    """Version dir may be ``v1.2.0/`` instead of ``version-1.2.0/``."""
    catalog = sample_catalog.parent / "catalog-vfolder"
    shutil.copytree(sample_catalog, catalog)
    art = catalog / "group-zenodo" / "artifact-example-artefact-one"
    shutil.move(art / "version-1", art / "v1.0.0")

    entries = scan_catalog(catalog)
    assert len(entries) == 1
    assert entries[0].version_file == art / "v1.0.0" / "version.jsonld"
