"""OEP identifier and keyword sanitization for table names and metadata."""

from __future__ import annotations

import re
from collections.abc import Iterable
from hashlib import sha1

MAX_OEP_IDENTIFIER_LEN = 50
MAX_OEP_KEYWORD_LEN = 40


def sanitize_oep_identifier(value: str | None, *, fallback: str = "resource") -> str:
    """Sanitize a string for use as an OEP table or dataset ``name``.

    Lowercase ASCII alphanumerics and underscores only; runs of other
    characters collapse to a single underscore.

    Parameters
    ----------
    value : str or None
        Raw identifier from source metadata.
    fallback : str, optional
        Value when ``value`` is empty or sanitizes to nothing (default ``"resource"``).

    Returns
    -------
    str
        Sanitized identifier.
    """
    raw = (value or "").strip().lower()
    if not raw:
        return fallback
    safe = re.sub(r"[^a-z0-9]+", "_", raw)
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe or fallback


def cut_oep_identifier(value: str, *, max_length: int = MAX_OEP_IDENTIFIER_LEN) -> str:
    """Truncate an OEP identifier with a deterministic hash suffix.

    When ``value`` exceeds ``max_length``, the stem is shortened and an
    8-character SHA-1 hex suffix is appended.

    Parameters
    ----------
    value : str
        Already-sanitized identifier.
    max_length : int, optional
        Maximum character length (default :data:`MAX_OEP_IDENTIFIER_LEN`).

    Returns
    -------
    str
        Identifier at most ``max_length`` characters.
    """
    trimmed = value.strip("_")
    if not trimmed:
        return "resource"
    if len(trimmed) <= max_length:
        return trimmed
    suffix = sha1(trimmed.encode("utf-8")).hexdigest()[:8]
    stem_budget = max_length - len(suffix) - 1
    if stem_budget < 1:
        return trimmed[:max_length]
    stem = trimmed[:stem_budget].rstrip("_")
    if not stem:
        stem = "r"
    return f"{stem}_{suffix}"[:max_length]


def sanitize_oep_keyword(value: str | None, *, max_length: int = MAX_OEP_KEYWORD_LEN) -> str:
    """Truncate a metadata keyword to OEP's maximum length.

    The OEP meta API rejects keywords longer than 40 characters. When a
    keyword exceeds ``max_length``, :func:`cut_oep_identifier` shortens it
    with a deterministic hash suffix.

    Parameters
    ----------
    value : str or None
        Raw keyword from a source record.
    max_length : int, optional
        Maximum keyword length (default :data:`MAX_OEP_KEYWORD_LEN`).

    Returns
    -------
    str
        Keyword at most ``max_length`` characters, or empty when ``value`` is
        missing/blank.
    """
    keyword = str(value or "").strip()
    if not keyword:
        return ""
    if len(keyword) <= max_length:
        return keyword
    return cut_oep_identifier(keyword, max_length=max_length)


def sanitize_oep_keywords(keywords: Iterable[str] | None) -> list[str]:
    """Sanitize OEMetadata ``keywords`` for OEP metadata upload.

    Parameters
    ----------
    keywords : iterable of str or None
        Raw keyword list from a source mapper.

    Returns
    -------
    list[str]
        Non-empty, de-duplicated keywords, each at most
        :data:`MAX_OEP_KEYWORD_LEN` characters.
    """
    out: list[str] = []
    seen: set[str] = set()
    for keyword in keywords or []:
        sanitized = sanitize_oep_keyword(keyword)
        if sanitized and sanitized not in seen:
            out.append(sanitized)
            seen.add(sanitized)
    return out
