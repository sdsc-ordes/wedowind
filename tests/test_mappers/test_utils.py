from __future__ import annotations

import importlib
import sys
import types


def _bootstrap_utils_module():
    fake_databusclient = types.SimpleNamespace(
        create_distribution=lambda **kwargs: kwargs,
        create_dataset=lambda version_id, **kwargs: {
            "version_id": version_id,
            **kwargs,
        },
        run=lambda *args, **kwargs: None,
    )
    sys.modules.setdefault("databusclient", fake_databusclient)
    return importlib.import_module("mappers.utils")


def test_sanitize_databus_uri_segment_strips_invalid_chars() -> None:
    utils_mod = _bootstrap_utils_module()
    assert (
        utils_mod.sanitize_databus_uri_segment("2026-04-26T06:15:34.063775")
        == "2026-04-26T06-15-34.063775"
    )
    assert utils_mod.normalize_databus_multi_segment_path("wedowind/world-bank-group") == (
        "wedowind/world-bank-group"
    )


def test_parse_iso_datetime_accepts_ckan_space_separated_timestamp() -> None:
    checkpoint_mod = importlib.import_module("mappers.checkpoint_state")
    dt = checkpoint_mod.parse_iso_datetime("2026-03-15 14:30:00.123456")
    assert dt is not None
    assert dt.year == 2026 and dt.month == 3 and dt.day == 15


def test_advance_source_state_incremental_keeps_newer_watermark() -> None:
    checkpoint_mod = importlib.import_module("mappers.checkpoint_state")
    first = checkpoint_mod.advance_source_state(
        {},
        [{"id": "a", "updated": "2026-05-01T12:00:00+00:00"}],
    )
    assert first["last_seen_dataset_id"] == "a"
    second = checkpoint_mod.advance_source_state(
        first,
        [{"id": "b", "updated": "2026-05-01T10:00:00+00:00"}],
    )
    assert second["last_seen_dataset_id"] == "a"
    assert second["last_seen_updated"] == first["last_seen_updated"]


def test_canonical_checkpoint_fills_defaults_and_drops_unknown_keys() -> None:
    import copy as copy_mod

    checkpoint_mod = importlib.import_module("mappers.checkpoint_state")
    assert checkpoint_mod.canonical_checkpoint(None) == copy_mod.deepcopy(checkpoint_mod.EMPTY_CHECKPOINT)
    raw = {
        "processed_dataset_ids": ["a", "b"],
        "last_seen_dataset_id": "a",
        "last_seen_updated": None,
        "last_run_at": "2026-01-01T00:00:00+00:00",
        "legacy_should_drop": True,
    }
    out = checkpoint_mod.canonical_checkpoint(raw)
    assert out["processed_dataset_ids"] == ["a", "b"]
    assert out["last_seen_dataset_id"] == "a"
    assert out["last_run_at"] == "2026-01-01T00:00:00+00:00"
    assert "legacy_should_drop" not in out


def test_get_databus_identifier_sanitizes_version_segment() -> None:
    utils_mod = _bootstrap_utils_module()
    vid = utils_mod.get_databus_identifier(
        "wedowind/world-bank-group",
        "vietnam-wind",
        "2026-04-26T06:15:34.063775",
    )
    assert "2026-04-26T06:15:34.063775" not in vid
    assert "06-15-34" in vid


def test_sanitize_dataset_text_fields_truncates_to_databus_limits() -> None:
    utils_mod = _bootstrap_utils_module()
    title, abstract, description = utils_mod.sanitize_dataset_text_fields(
        "t" * 120, "a" * 500, "d" * 700
    )
    assert len(title) == 100
    assert len(abstract) == 300
    assert len(description) == 300
