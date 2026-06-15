"""CKAN API helpers for OEP metadata mapping."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from ckanapi import RemoteCKAN

from mappers.oep.sanitize import sanitize_oep_identifier


def ckan_resource_file_format(resource: dict[str, Any]) -> str:
    """Return a normalized format token for a CKAN resource (defaults to ``txt``).

    Parameters
    ----------
    resource : dict
        Single CKAN resource dict from ``package_show``.

    Returns
    -------
    str
        Lowercase sanitized format token, or ``"txt"`` when missing or ``"none"``.
    """
    fmt = resource.get("format")
    if fmt is None:
        return "txt"
    s = str(fmt).strip().lower()
    if not s or s == "none":
        return "txt"
    return sanitize_oep_identifier(s, fallback="txt")


def scalar_ckan_text(value: Any) -> str | None:
    """Normalize CKAN text fields (lists, HTML) to plain scalar strings.

    Parameters
    ----------
    value : Any
        Raw CKAN field value (string, list, or ``None``).

    Returns
    -------
    str or None
        Plain text without HTML tags, or ``None`` when empty.
    """
    if value is None:
        return None
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if item is not None]
        joined = ", ".join(p for p in parts if p)
        return joined or None
    text = str(value)
    no_html = re.sub(r"<[^>]+>", " ", text)
    return " ".join(no_html.split()) or None


def iter_package_search_results(
    ckan: RemoteCKAN, params: dict[str, Any]
) -> Iterator[dict[str, Any]]:
    """Yield CKAN packages from paginated ``package_search`` results.

    Parameters
    ----------
    ckan : RemoteCKAN
        Configured CKAN API client.
    params : dict
        Base ``package_search`` parameters; ``rows`` and ``start`` are managed
        internally for pagination.

    Yields
    ------
    dict
        Package dicts from each ``package_search`` page until exhausted.
    """
    page_rows = int(params.get("rows") or 100)
    page_rows = max(1, min(page_rows, 1000))
    base = {k: v for k, v in params.items() if k not in {"rows", "start"}}
    start = 0
    page_num = 0
    while True:
        page_num += 1
        fq_preview = str(base.get("fq") or "")[:80]
        print(
            f"[ckan:api] package_search page={page_num} start={start} rows={page_rows} "
            f"fq_prefix={fq_preview!r} …",
            flush=True,
        )
        result = ckan.action.package_search(rows=page_rows, start=start, **base)
        if not isinstance(result, dict):
            print("[ckan:api] package_search: unexpected non-dict response; stopping.", flush=True)
            break
        batch = result.get("results") or []
        if not isinstance(batch, list):
            print("[ckan:api] package_search: unexpected results shape; stopping.", flush=True)
            break
        total = result.get("count")
        total_s = total if isinstance(total, int) else "?"
        print(
            f"[ckan:api] OK package_search got={len(batch)} total_count={total_s} "
            f"next_start={start + len(batch)}",
            flush=True,
        )
        for pkg in batch:
            if isinstance(pkg, dict):
                yield pkg
        if len(batch) < page_rows:
            break
        start += len(batch)
        if isinstance(total, int) and start >= total:
            break
