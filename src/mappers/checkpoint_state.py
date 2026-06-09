"""Incremental publish checkpoints for mapper timestamp JSON files.

Each entry tracks ``last_run_at``, ``last_seen_updated``, ``last_seen_dataset_id``,
and ``processed_dataset_ids``. Use :func:`canonical_checkpoint` to coerce partial or
unknown payloads to this schema (unknown keys are dropped).
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta
from typing import Any

EMPTY_CHECKPOINT: dict[str, Any] = {
    "last_run_at": None,
    "last_seen_updated": None,
    "last_seen_dataset_id": None,
    "processed_dataset_ids": [],
}


def parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse ISO or CKAN-style timestamps into UTC.

    Parameters
    ----------
    value : str or None
        Raw timestamp string, or ``None``.

    Returns
    -------
    datetime or None
        Timezone-aware UTC ``datetime`` when parsing succeeds; ``None`` when
        ``value`` is empty or unparsable.

    Notes
    -----
    Accepts CKAN-style ``YYYY-MM-DD HH:MM`` without a ``T`` separator between
    date and time.
    """
    if not value:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except ValueError:
        pass
    # CKAN sometimes returns "YYYY-MM-DD HH:MM:SS(.fff)?" without a T separator.
    if (
        len(normalized) >= 10
        and normalized[4] == "-"
        and normalized[7] == "-"
        and " " in normalized
        and "T" not in normalized[:19]
    ):
        alt = normalized.replace(" ", "T", 1)
        try:
            dt = datetime.fromisoformat(alt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except ValueError:
            return None
    return None


def entry_updated_at(entry: dict[str, Any]) -> datetime | None:
    """Parse ``updated`` from a checkpoint or search-hit row.

    Parameters
    ----------
    entry : dict[str, Any]
        Mapping that may contain ``updated`` (ISO string), typically with ``id``.

    Returns
    -------
    datetime or None
        Parsed UTC time, or ``None`` if missing or invalid.
    """
    return parse_iso_datetime(str(entry.get("updated") or ""))


def canonical_checkpoint(raw: Any) -> dict[str, Any]:
    """Coerce a value to the checkpoint schema using only canonical keys.

    Parameters
    ----------
    raw : Any
        Partial checkpoint dict, or non-dict (treated as empty).

    Returns
    -------
    dict[str, Any]
        Copy of :data:`EMPTY_CHECKPOINT` with values copied from ``raw`` for keys that
        exist in :data:`EMPTY_CHECKPOINT`. Other keys on ``raw`` are ignored.
    """
    if not isinstance(raw, dict):
        return copy.deepcopy(EMPTY_CHECKPOINT)
    out = copy.deepcopy(EMPTY_CHECKPOINT)
    for key in EMPTY_CHECKPOINT:
        if key in raw:
            out[key] = raw[key]
    return out


def filter_new_datasets(
    entries: list[dict[str, Any]], source_state: dict[str, Any], overlap_hours: int = 24
) -> list[dict[str, Any]]:
    """Return entries not yet covered by checkpoint watermarks.

    Parameters
    ----------
    entries : list[dict[str, Any]]
        Candidate rows with ``id`` and ``updated`` (e.g. Zenodo hits or CKAN-derived rows).
    source_state : dict[str, Any]
        Checkpoint fragment; coerced via :func:`canonical_checkpoint`.
    overlap_hours : int, optional
        Hours before ``last_seen_updated`` still eligible for re-processing when the id
        was seen (default ``24``).

    Returns
    -------
    list[dict[str, Any]]
        Subset of ``entries`` that should be processed in this run.
    """
    source_state = canonical_checkpoint(source_state)
    last_seen = parse_iso_datetime(str(source_state.get("last_seen_updated") or ""))
    seen_ids = set(source_state.get("processed_dataset_ids") or [])
    overlap = timedelta(hours=overlap_hours)
    threshold = last_seen - overlap if last_seen else None

    filtered: list[dict[str, Any]] = []
    for entry in entries:
        ds_id = str(entry.get("id") or "")
        updated_at = entry_updated_at(entry)
        if threshold and updated_at and updated_at < threshold and ds_id in seen_ids:
            continue
        if ds_id in seen_ids and (not updated_at or (last_seen and updated_at <= last_seen)):
            continue
        filtered.append(entry)
    return filtered


def advance_source_state(
    source_state: dict[str, Any],
    processed_datasets: list[dict[str, Any]],
    run_at: datetime | None = None,
    keep_last: int = 500,
) -> dict[str, Any]:
    """Merge processed rows into checkpoint state and advance watermarks.

    Parameters
    ----------
    source_state : dict[str, Any]
        Previous checkpoint; coerced via :func:`canonical_checkpoint` before merging.
    processed_datasets : list[dict[str, Any]]
        Rows with ``id`` and ``updated`` for datasets successfully handled this run.
    run_at : datetime or None, optional
        Wall time recorded as ``last_run_at`` (default: current UTC).
    keep_last : int, optional
        Maximum length of ``processed_dataset_ids`` deque tail (default ``500``).

    Returns
    -------
    dict[str, Any]
        New checkpoint dict including ``last_run_at``, ``processed_dataset_ids``,
        ``last_seen_updated``, and ``last_seen_dataset_id``.
    """
    next_state = canonical_checkpoint(source_state)
    now = run_at or datetime.now(UTC)
    next_state["last_run_at"] = now.isoformat()

    if not processed_datasets:
        return next_state

    known_ids = [str(x) for x in (next_state.get("processed_dataset_ids") or [])]
    merged_ids: list[str] = []
    for item in [*(str(rec.get("id") or "") for rec in processed_datasets), *known_ids]:
        if item and item not in merged_ids:
            merged_ids.append(item)
    next_state["processed_dataset_ids"] = merged_ids[:keep_last]

    prev_updated = parse_iso_datetime(str(next_state.get("last_seen_updated") or ""))
    prev_id = str(next_state.get("last_seen_dataset_id") or "")
    candidates: list[tuple[datetime, str]] = []
    if prev_updated:
        candidates.append((prev_updated, prev_id))
    for rec in processed_datasets:
        u = entry_updated_at(rec)
        rid = str(rec.get("id") or "")
        if u and rid:
            candidates.append((u, rid))
    if candidates:
        best_time, best_id = max(candidates, key=lambda t: (t[0], t[1]))
        next_state["last_seen_updated"] = best_time.isoformat()
        next_state["last_seen_dataset_id"] = best_id
    return next_state
