#!/usr/bin/env python3
"""Compare catalog metadata with OEP Databus and pull remote changes locally."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from databus_manager.objects.metadata import (
    ArtefactMetadata,
    CatalogVersionRef,
    GroupMetadata,
    VersionMetadata,
)

from databus_manager.scan_catalog import scan_catalog

from databus_manager.sparql import (
    SPARQL_URL_DEFAULT, 
    sparql_remote_version_exists
)

from databus_manager.fetch_remote import (
    fetch_remote_artefact,
    fetch_remote_group,
    fetch_remote_version,
    _coalesce_detection_timestamp,
    _optional_metadata_artefact,
    _optional_metadata_group,
    _optional_metadata_version,
)

def get_local(entry):
    local_group = GroupMetadata.from_jsonld_file(entry.group_file)
    local_artefact = ArtefactMetadata.from_jsonld_file(entry.artifact_file)
    local_version = VersionMetadata.from_jsonld_file(entry.version_file)
    return local_group, local_artefact, local_version

def get_remote(entry, sparql_url):
    exists = sparql_remote_version_exists(entry.version_id, sparql_url)
    raw_version = fetch_remote_version(entry.version_id, sparql_url) if exists else None
    raw_group = fetch_remote_group(entry.group_id, sparql_url) if exists else None
    raw_artefact = fetch_remote_artefact(entry.artifact_id, sparql_url) if exists else None

    remote_version = _optional_metadata_version(raw_version, entry.version_id)
    remote_group = _optional_metadata_group(raw_group, entry.group_id)
    remote_artefact = _optional_metadata_artefact(raw_artefact, entry.artifact_id)
    return exists, remote_version, remote_group, remote_artefact

def get_mismatches(remote_version, remote_group, remote_artefact, local_version, local_group, local_artefact):
    version_mismatch = bool(
        remote_version and not local_version.equals_normalized(remote_version)
    )
    group_mismatch = bool(remote_group and not local_group.equals_normalized(remote_group))
    artefact_mismatch = bool(
        remote_artefact and not local_artefact.equals_normalized(remote_artefact)
    )
    return version_mismatch, group_mismatch, artefact_mismatch

def apply_remote_to_local(
    entry: CatalogVersionRef,
    *,
    remote_version: VersionMetadata | None,
    remote_group: GroupMetadata | None,
    remote_artefact: ArtefactMetadata | None,
) -> None:
    if remote_version:
        VersionMetadata.write_remote_to_file(entry.version_file, remote_version)
    if remote_group:
        GroupMetadata.write_remote_to_file(entry.group_file, remote_group)
    if remote_artefact:
        ArtefactMetadata.write_remote_to_file(entry.artifact_file, remote_artefact)

def log_discrepancies(exists, local_group, remote_group, local_artefact, remote_artefact, local_version, remote_version, detection_timestamp):
    discrepancy_entries: list[dict[str, Any]] = []
    if exists:
        for e in local_group.discrepancies_vs(remote_group, timestamp=detection_timestamp):
            discrepancy_entries.append(e.to_dict())
        for e in local_artefact.discrepancies_vs(remote_artefact, timestamp=detection_timestamp):
            discrepancy_entries.append(e.to_dict())
        for e in local_version.discrepancies_vs(remote_version, timestamp=detection_timestamp):
            discrepancy_entries.append(e.to_dict())
    return discrepancy_entries

def compare_and_pull(
    catalog_root: Path,
    *,
    sparql_url: str = SPARQL_URL_DEFAULT,
    apply_changes: bool = False,
    detection_timestamp: str | None = None,
) -> list[dict[str, Any]]:
    """
    Compare local catalog with remote metadata.

    Returns one record per version with discrepancy flags and remote existence.
    """
    detection_timestamp = _coalesce_detection_timestamp(detection_timestamp)
    results: list[dict[str, Any]] = []
    for entry in scan_catalog(catalog_root):
        local_group, local_artefact, local_version = get_local(entry)
        exists, remote_version, remote_group, remote_artefact = get_remote(entry, sparql_url)

        version_mismatch, group_mismatch, artefact_mismatch = get_mismatches(
            remote_version, remote_group, remote_artefact, local_version, local_group, local_artefact
        )

        changed = False
        if apply_changes and exists and (version_mismatch or group_mismatch or artefact_mismatch):
            apply_remote_to_local(
                entry,
                remote_version=remote_version,
                remote_group=remote_group,
                remote_artefact=remote_artefact,
            )
            changed = True

        discrepancy_entries = log_discrepancies(exists, local_group, remote_group, local_artefact, remote_artefact, local_version, remote_version, detection_timestamp)
        

        results.append(
            {
                "version_id": entry.version_id,
                "group_id": entry.group_id,
                "artifact_id": entry.artifact_id,
                "version_file": str(entry.version_file),
                "group_file": str(entry.group_file),
                "artifact_file": str(entry.artifact_file),
                "remote_exists": exists,
                "version_mismatch": version_mismatch,
                "group_mismatch": group_mismatch,
                "artefact_mismatch": artefact_mismatch,
                "changed_local_from_remote": changed,
                "discrepancy_entries": discrepancy_entries,
            }
        )
    return results
