"""OEP API token resolution and metadata push via OMI."""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

import requests
from omi.api.oep import update_oep_tables_from_dataset_metadata
from omi.validation import validate_metadata

from mappers.oep.oep_table import OepTable

OEP_API_TOKEN_ENV = "OEP_API_TOKEN"


def oep_api_token(cli_override: str | None = None) -> str | None:
    """Resolve the OEP user API token from CLI or environment.

    Parameters
    ----------
    cli_override : str or None
        Value from ``--token`` when set.

    Returns
    -------
    str or None
        Non-empty token, or ``None`` if neither CLI nor :data:`OEP_API_TOKEN_ENV` provides one.
    """
    value = (cli_override or "").strip() or os.getenv(OEP_API_TOKEN_ENV)
    return value or None


def validate_oemetadata(metadata: dict[str, Any], *, check_license: bool = True) -> None:
    """Validate an OEMetadata document using OMI (JSON Schema + license checks).

    Parameters
    ----------
    metadata : dict[str, Any]
        Full OEMetadata mapping.
    check_license : bool, optional
        When ``True``, run SPDX-style license validation (default ``True``).

    Returns
    -------
    None

    Raises
    ------
    ValidationError
        When the document fails schema or license validation.
    """
    validate_metadata(metadata, check_license=check_license)


def push_oemetadata(
    metadata: dict[str, Any],
    *,
    token: str,
    method: str = "POST",
    timeout: int = 90,
    only_tables: Iterable[str] | None = None,
) -> dict[str, dict]:
    """Push dataset-level OEMetadata to one OEP table per resource (OMI).

    Parameters
    ----------
    metadata : dict[str, Any]
        OEMetadata with a non-empty ``resources`` list; each resource ``name`` is the OEP table.
    token : str
        OEP user API token (``Authorization: Token <token>``).
    method : str, optional
        ``POST`` or ``PUT`` for the meta API (default ``POST``).
    timeout : int, optional
        Request timeout in seconds (default ``90``).
    only_tables : iterable of str or None, optional
        Restrict updates to these table names.

    Returns
    -------
    dict[str, dict]
        Mapping from table name to OEP API JSON response.

    Raises
    ------
    MetadataError
        When ``resources`` is invalid or the OEP API returns an error.
    ValidationError
        When validation is run by the caller and fails before this function is invoked.
    """
    return update_oep_tables_from_dataset_metadata(
        metadata,
        token=token,
        method=method,
        timeout=timeout,
        only_tables=only_tables,
    )


def publish_to_oep(
    metadata: dict[str, Any],
    *,
    token: str,
    method: str = "POST",
    timeout: int = 90,
    only_tables: Iterable[str] | None = None,
    ensure_tables: bool = True,
    dry_run: bool = False,
    http_session: requests.Session | None = None,
) -> dict[str, dict]:
    """Create empty OEP tables (if needed) then push OEMetadata via OMI.

    Parameters
    ----------
    metadata : dict[str, Any]
        Full OEMetadata document.
    token : str
        OEP API token.
    method, timeout, only_tables
        Forwarded to :func:`push_oemetadata`.
    ensure_tables : bool
        When True, ``PUT`` empty table schemas before metadata POST.
    dry_run : bool
        Log table provisioning only; skip OEP writes.
    http_session : requests.Session or None
        Session for OEP table API (new session if omitted).

    Returns
    -------
    dict[str, dict]
        OEP meta API responses per table (empty dict when ``dry_run``).
    """
    session = http_session or requests.Session()
    push_tables = list(only_tables) if only_tables is not None else None
    if ensure_tables:
        ensured_tables = OepTable.ensure_for_metadata(
            session,
            metadata,
            token=token,
            dry_run=dry_run,
        )
        if push_tables is None:
            push_tables = ensured_tables
        else:
            ensured_set = set(ensured_tables)
            push_tables = [table for table in push_tables if table in ensured_set]
    if dry_run:
        return {}
    if push_tables is not None and not push_tables:
        print("[oep:meta] warning: no ensured tables available for metadata push; skipping.", flush=True)
        return {}
    return push_oemetadata(
        metadata,
        token=token,
        method=method,
        timeout=timeout,
        only_tables=push_tables,
    )
