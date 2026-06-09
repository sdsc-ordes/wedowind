"""SHA-256 + byte size for Databus distributions (Zenodo + CKAN).

Entry point for mappers: :func:`sha256_tuple_for_distribution_url` — tries API-declared
``sha256:…`` + ``size`` when ``resource`` matches that shape, otherwise streams the URL
(no disk files). Lower-level helpers :func:`declared_sha256_tuple_if_present` and
:func:`stream_sha256_hex_and_size` are available separately. Logs use ``[mapper:checksum]``.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

import requests
from requests.exceptions import (
    ChunkedEncodingError,
)
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
)
from requests.exceptions import Timeout as RequestsTimeout
from urllib3.exceptions import ProtocolError

CHECKSUM_STREAM_TIMEOUT = (30, 600)
CHECKSUM_PROGRESS_BYTES = 32 * 1024 * 1024
CHECKSUM_PROGRESS_SECONDS = 15.0

_STREAM_RETRY_ATTEMPTS = 5
_STREAM_RETRY_BASE_S = 3.0

_RETRIABLE_STREAM_ERRORS: tuple[type[BaseException], ...] = (
    ChunkedEncodingError,
    RequestsConnectionError,
    RequestsTimeout,
    ProtocolError,
    BrokenPipeError,
    ConnectionResetError,
)


def declared_sha256_tuple_if_present(resource: dict[str, Any]) -> tuple[str, int] | None:
    """Parse declared SHA-256 and size from API metadata when present.

    Expects the Zenodo ``files[]`` shape: ``checksum`` string ``sha256:<hex>`` and integer
    ``size``. The same keys appear on some other APIs; CKAN resources rarely match, so this
    usually returns ``None`` for CKAN and the caller streams the URL.

    Parameters
    ----------
    resource : dict[str, Any]
        Object that may contain ``checksum`` and ``size`` (e.g. Zenodo file dict).

    Returns
    -------
    tuple[str, int] or None
        ``(lowercase_hex, size_bytes)`` when checksum matches ``sha256:`` and size is valid;
        ``None`` otherwise.
    """
    chk = resource.get("checksum")
    if not isinstance(chk, str):
        return None
    lower = chk.strip().lower()
    if not lower.startswith("sha256:"):
        return None
    hexpart = chk.split(":", 1)[1].strip()
    try:
        if len(bytes.fromhex(hexpart)) != 32:
            return None
    except ValueError:
        return None
    sz = resource.get("size")
    if not isinstance(sz, int) or sz < 0:
        return None
    return hexpart.lower(), sz


def _stream_sha256_once(
    session: requests.Session,
    url: str,
    *,
    label: str,
    expected_size: int | None = None,
) -> tuple[str, int]:
    """Stream one HTTP GET response and compute SHA-256 plus byte length.

    Parameters
    ----------
    session : requests.Session
        Session used for the GET request.
    url : str
        File download URL.
    label : str
        Label for progress logs.
    expected_size : int or None, optional
        Declared size for progress percentage logs.

    Returns
    -------
    tuple[str, int]
        ``(sha256_hex_lower, total_bytes_read)``.

    Raises
    ------
    requests.HTTPError
        When the response status is not successful.
    """
    digest = hashlib.sha256()
    total = 0
    t0 = time.monotonic()
    last_log_at = t0
    last_log_total = 0
    with session.get(url, stream=True, timeout=CHECKSUM_STREAM_TIMEOUT) as resp:
        resp.raise_for_status()
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if not chunk:
                continue
            digest.update(chunk)
            total += len(chunk)
            now = time.monotonic()
            if (
                total - last_log_total >= CHECKSUM_PROGRESS_BYTES
                or now - last_log_at >= CHECKSUM_PROGRESS_SECONDS
            ):
                pct = ""
                if expected_size and expected_size > 0:
                    pct = f" ({100.0 * total / expected_size:.1f}% of declared size)"
                print(
                    f"[mapper:checksum] {label!r}: hashed {total} bytes{pct} …",
                    flush=True,
                )
                last_log_at = now
                last_log_total = total
    return digest.hexdigest(), total


def stream_sha256_hex_and_size(
    session: requests.Session,
    url: str,
    *,
    label: str,
    expected_size: int | None = None,
) -> tuple[str, int]:
    """Stream URL to compute SHA-256 and length with retries on transient errors.

    Parameters
    ----------
    session : requests.Session
        Session for streaming GET.
    url : str
        Download URL.
    label : str
        Label for logs.
    expected_size : int or None, optional
        Declared byte length for progress logs.

    Returns
    -------
    tuple[str, int]
        ``(sha256_hex_lower, byte_length)``.

    Raises
    ------
    BaseException
        The last error from :func:`_stream_sha256_once` if all retry attempts fail.
    """
    last_err: BaseException | None = None
    for attempt in range(1, _STREAM_RETRY_ATTEMPTS + 1):
        try:
            return _stream_sha256_once(session, url, label=label, expected_size=expected_size)
        except _RETRIABLE_STREAM_ERRORS as err:
            last_err = err
            if attempt >= _STREAM_RETRY_ATTEMPTS:
                break
            wait = min(120.0, _STREAM_RETRY_BASE_S * (2 ** (attempt - 1)))
            print(
                f"[mapper:checksum] {label!r}: stream interrupted ({type(err).__name__}: {err}); "
                f"retry {attempt}/{_STREAM_RETRY_ATTEMPTS} in {wait:.0f}s …",
                flush=True,
            )
            time.sleep(wait)
    raise last_err


def sha256_tuple_for_distribution_url(
    session: requests.Session,
    url: str,
    *,
    label: str,
    expected_size: int | None = None,
    resource: dict[str, Any] | None = None,
) -> tuple[str, int]:
    """SHA-256 and byte length for a distribution: declared metadata if possible, else stream ``url``.

    Shared by Zenodo and CKAN mappers. Declared checksum uses :func:`declared_sha256_tuple_if_present`
    (Zenodo ``files[]`` / compatible ``checksum`` + ``size``). CKAN resources usually do not match and
    this falls through to :func:`stream_sha256_hex_and_size`.

    Parameters
    ----------
    session : requests.Session
        Session used when streaming is required.
    url : str
        File download URL (always used when streaming).
    label : str
        Label for logs.
    expected_size : int or None, optional
        Declared size for progress when streaming.
    resource : dict or None, optional
        Optional API row (e.g. Zenodo file dict, CKAN resource). When ``None``, streams ``url``.

    Returns
    -------
    tuple[str, int]
        ``(sha256_hex_lower, byte_length)``.
    """
    if resource is not None:
        declared = declared_sha256_tuple_if_present(resource)
        if declared is not None:
            print(
                f"[mapper:checksum] {label!r}: using declared sha256 (no download)",
                flush=True,
            )
            return declared
    return stream_sha256_hex_and_size(session, url, label=label, expected_size=expected_size)
