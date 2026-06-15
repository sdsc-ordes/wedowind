"""Extract CKAN license fields and build OEMetadata ``licenses`` entries."""

from __future__ import annotations

from typing import Any

from mappers.oep.licenses import build_oemetadata_licenses, resolve_license_iri
from mappers.oep.oemetadata import OemetadataLicense


def extract_license_iri(package: dict[str, Any]) -> str:
    """Extract a canonical license IRI from a CKAN package dict.

    Parameters
    ----------
    package : dict
        CKAN ``package_show`` result.

    Returns
    -------
    str
        Resolved license IRI, or an empty string when no license is found.
    """
    for candidate in (package.get("license_url"), package.get("license_id")):
        if not isinstance(candidate, str):
            continue
        s = candidate.strip()
        if not s:
            continue
        if s.lower().startswith(("http://", "https://")):
            return s
    for candidate in (package.get("license_url"), package.get("license_id")):
        if isinstance(candidate, str) and candidate.strip():
            mapped = resolve_license_iri(candidate)
            if mapped:
                return mapped
    return ""


def build_oemetadata_licenses_from_package(package: dict[str, Any]) -> list[OemetadataLicense]:
    """Build OEMetadata ``licenses`` from a CKAN ``package_show`` result.

    Parameters
    ----------
    package : dict
        CKAN ``package_show`` result.

    Returns
    -------
    list[OemetadataLicense]
        OEMetadata license entries derived from package license fields.
    """
    iri = extract_license_iri(package)
    if not iri:
        license_id = package.get("license_id")
        if isinstance(license_id, str) and license_id.strip():
            iri = resolve_license_iri(license_id)
    return build_oemetadata_licenses(iri)
