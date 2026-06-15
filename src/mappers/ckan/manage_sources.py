"""Load and persist CKAN registry JSON and per-query timestamp checkpoints."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from mappers.checkpoint_state import EMPTY_CHECKPOINT, canonical_checkpoint

DEFAULT_SOURCES_PATH = Path(__file__).resolve().parent / "config" / "sources.json"
DEFAULT_TIMESTAMP_PATH = Path(__file__).resolve().parent / "config" / "timestamp.json"


def resolve_ckan_sources_file(requested: Path) -> Path:
    """Resolve a CKAN sources JSON path.

    Parameters
    ----------
    requested : pathlib.Path
        Candidate config path.

    Returns
    -------
    pathlib.Path
        Same as ``requested`` when it exists.

    Raises
    ------
    FileNotFoundError
        If ``requested`` is not a file.
    """
    if requested.is_file():
        return requested
    raise FileNotFoundError(f"CKAN sources config not found: {requested}")


def load_ckan_sources(path: Path = DEFAULT_SOURCES_PATH) -> dict[str, Any]:
    """Load CKAN registry JSON (top-level ``sources`` or legacy ``providers``).

    Parameters
    ----------
    path : pathlib.Path, optional
        Config path (default: :data:`DEFAULT_SOURCES_PATH`).

    Returns
    -------
    dict[str, Any]
        ``{'sources': {source_id: {... 'queries': [...] }}}``.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If JSON is invalid or missing ``sources`` / ``providers``.
    """
    config_file = resolve_ckan_sources_file(path)
    data = json.loads(config_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid CKAN sources config format in {config_file}")

    raw = data.get("sources") or data.get("providers")
    if raw is None:
        raise ValueError(
            f"CKAN sources config must contain top-level 'sources' (or legacy 'providers'): {config_file}"
        )
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"Invalid or empty sources/providers section in {config_file}")

    normalized: dict[str, Any] = {}
    for source_id, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        queries_list = entry.get("queries") or entry.get("sources")
        if not isinstance(queries_list, list):
            queries_list = []
        rest = {k: v for k, v in entry.items() if k not in ("sources", "queries")}
        normalized[source_id] = {**rest, "queries": queries_list}

    return {"sources": normalized}


def _normalize_timestamp_document(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy timestamp JSON shape to ``sources`` / ``queries`` only.

    Parameters
    ----------
    data : dict[str, Any]
        Root object from a timestamp file.

    Returns
    -------
    dict[str, Any]
        ``{'sources': {source_id: {'queries': {query_id: ...}}}}``; empty
        ``sources`` when the top-level shape is unknown.
    """
    top = data.get("sources") or data.get("providers")
    if not isinstance(top, dict):
        return {"sources": {}}
    out: dict[str, Any] = {"sources": {}}
    for source_id, block in top.items():
        if not isinstance(block, dict):
            continue
        inner = block.get("queries") or block.get("sources")
        if not isinstance(inner, dict):
            inner = {}
        out["sources"][source_id] = {"queries": dict(inner)}
    return out


def _empty_timestamp_skeleton(
    sources_path: Path = DEFAULT_SOURCES_PATH,
) -> dict[str, Any]:
    """Build default nested checkpoints for every query id in the sources registry.

    Parameters
    ----------
    sources_path : pathlib.Path, optional
        Path passed to :func:`load_ckan_sources` (default: :data:`DEFAULT_SOURCES_PATH`).

    Returns
    -------
    dict[str, Any]
        Tree with :data:`mappers.checkpoint_state.EMPTY_CHECKPOINT` per query id.
    """
    cfg = load_ckan_sources(path=sources_path)
    sources = cfg.get("sources") or {}
    default_state: dict[str, Any] = {"sources": {}}
    for source_id, entry in sources.items():
        if not isinstance(entry, dict):
            continue
        queries_state: dict[str, Any] = {}
        for q in entry.get("queries") or []:
            if isinstance(q, dict) and isinstance(q.get("id"), str):
                queries_state[q["id"]] = copy.deepcopy(EMPTY_CHECKPOINT)
        default_state["sources"][source_id] = {"queries": queries_state}
    return default_state


def load_ckan_timestamp_state(
    path: Path = DEFAULT_TIMESTAMP_PATH,
    *,
    sources_path: Path = DEFAULT_SOURCES_PATH,
) -> dict[str, Any]:
    """Load nested source/query checkpoints merged with the registry skeleton.

    Parameters
    ----------
    path : pathlib.Path, optional
        Timestamp file (default: :data:`DEFAULT_TIMESTAMP_PATH`).
    sources_path : pathlib.Path, optional
        Registry used to build the default query keys (default: :data:`DEFAULT_SOURCES_PATH`).

    Returns
    -------
    dict[str, Any]
        Merged state; unknown top-level keys from the file are dropped if not in the skeleton.
    """
    default_state = _empty_timestamp_skeleton(sources_path)

    if not path.is_file():
        return copy.deepcopy(default_state)

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return copy.deepcopy(default_state)

    loaded = _normalize_timestamp_document(data)
    if not isinstance(loaded.get("sources"), dict):
        return copy.deepcopy(default_state)

    merged = copy.deepcopy(default_state)
    for source_id, source_state in loaded["sources"].items():
        if source_id not in merged["sources"] or not isinstance(source_state, dict):
            continue
        loaded_queries = source_state.get("queries")
        if not isinstance(loaded_queries, dict):
            continue
        for query_id, query_state in loaded_queries.items():
            if query_id not in merged["sources"][source_id]["queries"]:
                continue
            if isinstance(query_state, dict):
                merged["sources"][source_id]["queries"][query_id] = canonical_checkpoint(
                    {
                        **merged["sources"][source_id]["queries"][query_id],
                        **query_state,
                    }
                )
    return merged


def save_ckan_timestamp_state(
    state: dict[str, Any],
    path: Path = DEFAULT_TIMESTAMP_PATH,
    *,
    enabled: bool = True,
) -> None:
    """Write CKAN timestamp JSON via a temp file and atomic replace.

    Parameters
    ----------
    state : dict[str, Any]
        Full document to persist.
    path : pathlib.Path, optional
        Destination path (default: :data:`DEFAULT_TIMESTAMP_PATH`).
    enabled : bool, optional
        When ``False``, the write is skipped (default: ``True``).

    Returns
    -------
    None
    """
    if not enabled:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, indent=2) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)
