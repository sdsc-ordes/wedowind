"""Extract Zenodo license fields and build OEMetadata ``licenses`` entries."""

from __future__ import annotations

from typing import Any

from mappers.oep.licenses import build_oemetadata_licenses, resolve_license_iri
from mappers.oep.oemetadata import OemetadataLicense


def extract_license_iri(metadata: dict[str, Any]) -> str:
    """Extract a canonical license IRI from Zenodo record metadata.

    Parameters
    ----------
    metadata : dict
        Zenodo record ``metadata`` object.

    Returns
    -------
    str
        Resolved license IRI, or an empty string when no license is found.
    """
    license_data = metadata.get("license")
    if isinstance(license_data, dict):
        url = license_data.get("url")
        if isinstance(url, str) and url.strip():
            u = url.strip()
            if u.lower().startswith(("http://", "https://")):
                return u
        tid = license_data.get("id")
        if tid is not None:
            return resolve_license_iri(str(tid))
        if isinstance(url, str) and url.strip():
            return resolve_license_iri(url.strip())
        return ""
    return resolve_license_iri(str(license_data) if license_data else None)


def build_oemetadata_licenses_from_metadata(metadata: dict[str, Any]) -> list[OemetadataLicense]:
    """Build OEMetadata ``licenses`` from a Zenodo ``metadata`` object.

    Parameters
    ----------
    metadata : dict
        Zenodo record ``metadata`` object.

    Returns
    -------
    list[OemetadataLicense]
        OEMetadata license entries derived from the record license fields.
    """
    return build_oemetadata_licenses(extract_license_iri(metadata))
