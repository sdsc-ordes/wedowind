from __future__ import annotations

from databus_manager.compare_catalog_with_databus import get_mismatches, log_discrepancies
from databus_manager.objects.metadata import ArtefactMetadata, GroupMetadata, VersionMetadata


def _version(title: str) -> VersionMetadata:
    return VersionMetadata(
        entity_id="v",
        title=title,
        abstract="a",
        description="d",
        license="l",
        distribution=[{"downloadURL": "u", "formatExtension": "zip", "compression": "none"}],
    )


def test_get_mismatches_flags_only_changed_entities() -> None:
    local_group = GroupMetadata("g", "t1", "a", "d")
    remote_group = GroupMetadata("g", "t1", "a", "d")
    local_art = ArtefactMetadata("a", "x", "a", "d")
    remote_art = ArtefactMetadata("a", "y", "a", "d")
    local_ver = _version("t1")
    remote_ver = _version("t1")

    version_mismatch, group_mismatch, artefact_mismatch = get_mismatches(
        remote_ver, remote_group, remote_art, local_ver, local_group, local_art
    )
    assert version_mismatch is False
    assert group_mismatch is False
    assert artefact_mismatch is True


def test_log_discrepancies_empty_if_not_exists() -> None:
    local_group = GroupMetadata("g", "t1", "a", "d")
    local_art = ArtefactMetadata("a", "t1", "a", "d")
    local_ver = _version("t1")
    rows = log_discrepancies(
        False, local_group, None, local_art, None, local_ver, None, "2026-01-01T00:00:00+00:00"
    )
    assert rows == []
