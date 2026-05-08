"""Normalize license strings from Zenodo/CKAN metadata to absolute http(s) IRIs for Databus JSON-LD."""

from __future__ import annotations

from typing import Any

# Short tokens (CKAN registry ids, Zenodo license.id, SPDX-style) → canonical license URL.
LICENSE_SHORT_CODE_TO_IRI: dict[str, str] = {
    "cc0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "cc0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "cc-zero": "https://creativecommons.org/publicdomain/zero/1.0/",
    "cc-by": "https://creativecommons.org/licenses/by/4.0/",
    "cc-by-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "cc-by-sa": "https://creativecommons.org/licenses/by-sa/4.0/",
    "cc-by-sa-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "cc-by-nc": "https://creativecommons.org/licenses/by-nc/4.0/",
    "cc-by-nc-4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
    "cc-by-nd": "https://creativecommons.org/licenses/by-nd/4.0/",
    "cc-by-nc-sa": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    "cc-by-nc-nd": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
    "odc-by": "https://opendatacommons.org/licenses/by/1-0/",
    "odc-odbl": "https://opendatacommons.org/licenses/odbl/1-0/",
    "odbl-1.0": "https://opendatacommons.org/licenses/odbl/1-0/",
    "uk-ogl": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
}


def normalize_license_value_for_databus(value: str | None) -> str:
    """Map a bare license token to an https IRI when known; pass through full URLs.

    Parameters
    ----------
    value : str or None
        License string or short code.

    Returns
    -------
    str
        Absolute ``http(s)`` IRI, mapped short code, or empty string if unknown/empty.
    """
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    if s.lower().startswith(("http://", "https://")):
        return s
    return LICENSE_SHORT_CODE_TO_IRI.get(s.lower(), "")


def normalize_ckan_license_for_databus(pkg: dict[str, Any]) -> str:
    """Resolve a license IRI from CKAN ``package_show`` metadata.

    Parameters
    ----------
    pkg : dict[str, Any]
        CKAN package dict (expects ``license_url`` / ``license_id``).

    Returns
    -------
    str
        Best-effort ``http(s)`` license IRI, or empty string if none resolved.
    """
    for candidate in (pkg.get("license_url"), pkg.get("license_id")):
        if not isinstance(candidate, str):
            continue
        s = candidate.strip()
        if not s:
            continue
        if s.lower().startswith(("http://", "https://")):
            return s
    for candidate in (pkg.get("license_url"), pkg.get("license_id")):
        if isinstance(candidate, str) and candidate.strip():
            mapped = normalize_license_value_for_databus(candidate)
            if mapped:
                return mapped
    return ""


def normalize_zenodo_license_for_databus(metadata: dict[str, Any]) -> str:
    """Resolve a license IRI from Zenodo ``metadata.license``.

    Parameters
    ----------
    metadata : dict[str, Any]
        Zenodo ``metadata`` object (``license`` may be dict with ``id``/``url`` or string).

    Returns
    -------
    str
        Best-effort ``http(s)`` license IRI, or empty string if none resolved.
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
            return normalize_license_value_for_databus(str(tid))
        if isinstance(url, str) and url.strip():
            return normalize_license_value_for_databus(url.strip())
        return ""
    return normalize_license_value_for_databus(str(license_data) if license_data else None)
