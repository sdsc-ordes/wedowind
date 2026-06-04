"""Load Zenodo sources JSON and persist per-source timestamp checkpoints."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from mappers.checkpoint_state import EMPTY_CHECKPOINT, canonical_checkpoint

DEFAULT_SOURCES_PATH = Path(__file__).resolve().parent / "config" / "sources.json"
DEFAULT_TIMESTAMP_PATH = Path(__file__).resolve().parent / "config" / "timestamp.json"


class ZenodoMapperError(RuntimeError):
    """Raised when Zenodo mapper configuration cannot be loaded or is invalid."""


def _parse_sources_section(data: dict[str, Any], path: Path) -> dict[str, dict[str, str]]:
    """Parse ``sources`` (or a flat top-level mapping) into query params per key.

    Parameters
    ----------
    data : dict[str, Any]
        Parsed JSON root object.
    path : pathlib.Path
        Source path (for error messages).

    Returns
    -------
    dict[str, dict[str, str]]
        Mapping ``source_key -> query parameter strings`` for Zenodo ``/api/records``.

    Raises
    ------
    ZenodoMapperError
        If sections are missing, empty, or malformed.
    """
    if "sources" in data:
        source_map = data.get("sources")
        if not isinstance(source_map, dict):
            raise ZenodoMapperError(f"Invalid 'sources' section in {path}")
    else:
        source_map = data

    parsed: dict[str, dict[str, str]] = {}
    for source_key, source_params in source_map.items():
        if not isinstance(source_key, str) or not source_key.strip():
            raise ZenodoMapperError(f"Invalid source key in {path}: {source_key!r}")
        if not isinstance(source_params, dict):
            raise ZenodoMapperError(f"Invalid query params for source {source_key!r} in {path}")
        filtered = {
            str(key): str(value)
            for key, value in source_params.items()
            if isinstance(key, str) and isinstance(value, (str, int, float, bool))
        }
        if not filtered:
            raise ZenodoMapperError(
                f"Source {source_key!r} has no valid query parameters in {path}"
            )
        parsed[source_key] = filtered

    if not parsed:
        raise ZenodoMapperError(f"No valid source definitions found in {path}")
    return parsed


def load_source_config(path: Path = DEFAULT_SOURCES_PATH) -> dict[str, Any]:
    """Load Zenodo ``sources.json``: ``defaults.oep`` plus query params per source key.

    Parameters
    ----------
    path : pathlib.Path, optional
        Path to JSON config (default: :data:`DEFAULT_SOURCES_PATH`).

    Returns
    -------
    dict
        ``{"defaults": {...}, "sources": {source_key: query_params}}``.

    Raises
    ------
    ZenodoMapperError
        If the file is missing, malformed, or missing a valid ``defaults`` section.
    """
    if not path.is_file():
        raise ZenodoMapperError(f"Zenodo sources config not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ZenodoMapperError(f"Invalid source query config format in {path}")

    sources = _parse_sources_section(data, path)
    defaults_section = data.get("defaults")
    if defaults_section is None or not isinstance(defaults_section, dict):
        raise ZenodoMapperError(f"Missing or invalid 'defaults' section in {path}")

    return {"defaults": defaults_section, "sources": sources}


def load_source_query_params(
    path: Path = DEFAULT_SOURCES_PATH,
) -> dict[str, dict[str, str]]:
    """Return only the ``sources`` map from :func:`load_source_config`.

    Parameters
    ----------
    path : pathlib.Path, optional
        Path to JSON config (default: :data:`DEFAULT_SOURCES_PATH`).

    Returns
    -------
    dict[str, dict[str, str]]
        Zenodo API query parameters keyed by source id.

    Raises
    ------
    ZenodoMapperError
        Propagated from :func:`load_source_config`.
    """
    return load_source_config(path=path)["sources"]


try:
    SOURCE_QUERY_PARAMS = load_source_query_params()
except Exception:
    SOURCE_QUERY_PARAMS = {}
DEFAULT_TIMESTAMP_STATE = {
    source_key: copy.deepcopy(EMPTY_CHECKPOINT) for source_key in SOURCE_QUERY_PARAMS
}


def load_timestamp_state(path: Path = DEFAULT_TIMESTAMP_PATH) -> dict[str, Any]:
    """Load per-source checkpoints merged with the skeleton from ``sources.json`` keys.

    Parameters
    ----------
    path : pathlib.Path, optional
        Timestamp JSON path (default: :data:`DEFAULT_TIMESTAMP_PATH`).

    Returns
    -------
    dict[str, Any]
        Mapping ``source_key -> checkpoint dict`` (canonical schema).
    """
    if not path.is_file():
        return copy.deepcopy(DEFAULT_TIMESTAMP_STATE)

    data = json.loads(path.read_text(encoding="utf-8"))
    state = copy.deepcopy(DEFAULT_TIMESTAMP_STATE)
    for source_key in state:
        if isinstance(data.get(source_key), dict):
            state[source_key] = canonical_checkpoint({**state[source_key], **data[source_key]})
    return state


def save_timestamp_state(
    state: dict[str, Any],
    path: Path = DEFAULT_TIMESTAMP_PATH,
    *,
    enabled: bool = True,
) -> None:
    """Write Zenodo timestamp JSON to disk.

    Parameters
    ----------
    state : dict[str, Any]
        Full timestamp document to serialize.
    path : pathlib.Path, optional
        Output path (default: :data:`DEFAULT_TIMESTAMP_PATH`).
    enabled : bool, optional
        When ``False``, the write is skipped (default: ``True``).

    Returns
    -------
    None
    """
    if not enabled:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
