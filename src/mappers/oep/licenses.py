"""Map license strings and IRIs to OEMetadata ``licenses`` entries.

Pipeline stages
---------------
1. **Resolve** — turn a bare license code or URL into a canonical https IRI
   (:func:`resolve_license_iri`).
2. **Extract** — read license fields from a source record (Zenodo/CKAN modules).
3. **Build** — construct :class:`~mappers.oep.oemetadata.OemetadataLicense` instances from an IRI
   (:func:`build_oemetadata_license`, :func:`build_oemetadata_licenses`).
"""

from __future__ import annotations

from mappers.oep.oemetadata import OemetadataLicense

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

LICENSE_IRI_TO_OEM_NAME: dict[str, str] = {
    "https://creativecommons.org/publicdomain/zero/1.0/": "CC0-1.0",
    "https://creativecommons.org/licenses/by/4.0/": "CC-BY-4.0",
    "https://creativecommons.org/licenses/by-sa/4.0/": "CC-BY-SA-4.0",
    "https://creativecommons.org/licenses/by-nc/4.0/": "CC-BY-NC-4.0",
    "https://opendatacommons.org/licenses/odbl/1-0/": "ODbL-1.0",
    "https://opendatacommons.org/licenses/by/1-0/": "ODC-By-1.0",
}


def resolve_license_iri(value: str | None) -> str:
    """Resolve a short license code or URL to a canonical https IRI.

    Parameters
    ----------
    value : str or None
        SPDX-style short code (e.g. ``"cc-by-4.0"``) or license URL.

    Returns
    -------
    str
        Canonical https IRI when recognized; empty string when ``value`` is
        missing or unknown.
    """
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    if s.lower().startswith(("http://", "https://")):
        return s
    return LICENSE_SHORT_CODE_TO_IRI.get(s.lower(), "")


def oemetadata_name_for_iri(iri: str) -> str:
    """Derive an OEMetadata ``licenses[].name`` token from a license IRI.

    Parameters
    ----------
    iri : str
        Resolved license IRI.

    Returns
    -------
    str
        SPDX-style name (e.g. ``"CC-BY-4.0"``), or a fallback derived from the
        IRI path tail.
    """
    normalized = iri.rstrip("/") + ("" if iri.endswith("/") else "")
    for key, name in LICENSE_IRI_TO_OEM_NAME.items():
        if key.rstrip("/") == normalized.rstrip("/"):
            return name
    for token, mapped in LICENSE_SHORT_CODE_TO_IRI.items():
        if mapped.rstrip("/") == normalized.rstrip("/"):
            return token.upper().replace("ODC-ODBL", "ODbL-1.0")
    tail = normalized.split("/")[-1] or "unknown"
    return tail.replace(".", "-")[:32] or "unknown"


def build_oemetadata_license(iri: str, *, attribution: str | None = None) -> OemetadataLicense:
    """Build one OEMetadata ``licenses`` object from a license IRI.

    Parameters
    ----------
    iri : str
        Resolved license IRI (``path`` field).
    attribution : str or None, optional
        ``attribution`` text; ``"ToDo"`` when omitted.

    Returns
    -------
    OemetadataLicense
        Single OEMetadata license entry.
    """
    name = oemetadata_name_for_iri(iri)
    return OemetadataLicense(
        name=name,
        title=name,
        path=iri,
        instruction="ToDo",
        attribution=attribution or "ToDo",
    )


def build_oemetadata_licenses(
    iri: str, *, attribution: str | None = None
) -> list[OemetadataLicense]:
    """Build OEMetadata ``licenses`` list from a resolved IRI.

    Parameters
    ----------
    iri : str
        Resolved license IRI from :func:`resolve_license_iri`.
    attribution : str or None, optional
        Passed through to :func:`build_oemetadata_license`.

    Returns
    -------
    list[OemetadataLicense]
        One-element list when ``iri`` is non-empty; empty list otherwise.
    """
    if not iri:
        return []
    return [build_oemetadata_license(iri, attribution=attribution)]
