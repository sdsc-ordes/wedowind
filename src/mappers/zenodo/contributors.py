"""Map Zenodo creators to OEMetadata contributors."""

from __future__ import annotations

from typing import Any

from mappers.oep.oemetadata import OemetadataContributor


def contributors_from_metadata(metadata: dict[str, Any]) -> list[OemetadataContributor]:
    """Map Zenodo ``creators`` to OEMetadata ``contributors`` (best effort).

    Parameters
    ----------
    metadata : dict
        Zenodo record ``metadata`` object.

    Returns
    -------
    list[OemetadataContributor]
        OEMetadata contributor entries; empty when ``creators`` is absent or invalid.
    """
    creators = metadata.get("creators")
    if not isinstance(creators, list):
        return []
    entries: list[dict[str, Any]] = []
    for creator in creators:
        if not isinstance(creator, dict):
            continue
        name = creator.get("name") or creator.get("family") or ""
        if not str(name).strip():
            continue
        entries.append(
            {
                "title": str(name).strip(),
                "path": creator.get("orcid") or None,
                "organization": creator.get("affiliation") or None,
                "comment": "Mapped from Zenodo creators",
            }
        )
    return OemetadataContributor.from_entries(entries)
