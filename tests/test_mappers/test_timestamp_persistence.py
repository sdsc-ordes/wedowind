from __future__ import annotations

import json
from pathlib import Path

from mappers.ckan.manage_sources import save_ckan_timestamp_state
from mappers.zenodo.manage_sources import save_timestamp_state


def _read_json(path: Path) -> dict:
    """Load JSON from a path for test assertions."""
    return json.loads(path.read_text(encoding="utf-8"))


def test_save_timestamp_state_skips_write_when_disabled(tmp_path: Path) -> None:
    """Zenodo timestamp files are not written when persistence is disabled."""
    target = tmp_path / "zenodo" / "timestamp.json"
    state = {"source": {"processed_dataset_ids": ["abc"]}}

    save_timestamp_state(state, path=target, enabled=False)

    assert not target.exists()


def test_save_timestamp_state_writes_when_enabled(tmp_path: Path) -> None:
    """Zenodo timestamp files are written when persistence is enabled."""
    target = tmp_path / "zenodo" / "timestamp.json"
    state = {"source": {"processed_dataset_ids": ["abc"]}}

    save_timestamp_state(state, path=target, enabled=True)

    assert _read_json(target) == state


def test_save_ckan_timestamp_state_skips_write_when_disabled(tmp_path: Path) -> None:
    """CKAN timestamp files are not written when persistence is disabled."""
    target = tmp_path / "ckan" / "timestamp.json"
    state = {"sources": {"foo": {"queries": {}}}}

    save_ckan_timestamp_state(state, path=target, enabled=False)

    assert not target.exists()


def test_save_ckan_timestamp_state_writes_when_enabled(tmp_path: Path) -> None:
    """CKAN timestamp files are written when persistence is enabled."""
    target = tmp_path / "ckan" / "timestamp.json"
    state = {"sources": {"foo": {"queries": {}}}}

    save_ckan_timestamp_state(state, path=target, enabled=True)

    assert _read_json(target) == state
