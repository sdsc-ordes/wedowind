"""Map CKAN author fields to OEMetadata contributors."""

from __future__ import annotations

from typing import Any

from mappers.oep.oemetadata import OemetadataContributor


def contributors_from_package(pkg: dict[str, Any]) -> list[OemetadataContributor]:
    """Map CKAN author/maintainer fields to OEMetadata ``contributors``.

    Parameters
    ----------
    pkg : dict
        CKAN ``package_show`` result.

    Returns
    -------
    list[OemetadataContributor]
        OEMetadata contributor entries; empty when ``author`` is absent or blank.
    """
    author = pkg.get("author")
    if not isinstance(author, str) or not author.strip():
        return []
    return OemetadataContributor.from_entries(
        [
            {
                "title": author.strip(),
                "path": None,
                "organization": pkg.get("author_email"),
                "comment": "Mapped from CKAN author",
            }
        ]
    )
