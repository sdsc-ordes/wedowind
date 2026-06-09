from __future__ import annotations

import importlib
import sys
import types
from datetime import UTC, datetime

import pytest


def _bootstrap_mapper_imports():
    fake_databusclient = types.SimpleNamespace(
        create_distribution=lambda **kwargs: kwargs,
        create_dataset=lambda version_id, **kwargs: {
            "version_id": version_id,
            **kwargs,
        },
        run=lambda *args, **kwargs: None,
    )
    sys.modules.setdefault("databusclient", fake_databusclient)
    utils_mod = importlib.import_module("mappers.utils")
    zenodo_mod = importlib.import_module("mappers.zenodo.mapper")
    checkpoint_mod = importlib.import_module("mappers.checkpoint_state")
    return utils_mod, zenodo_mod, checkpoint_mod


def test_zenodo_mapper_maps_record_and_enforces_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    utils_mod, zenodo_mod, _checkpoint_mod = _bootstrap_mapper_imports()
    record = {
        "id": 42,
        "updated": "2026-05-01T12:00:00+00:00",
        "metadata": {
            "title": "T" * 130,
            "description": "<p>" + ("A" * 400) + "</p>",
            "license": {"id": "cc-by-4.0"},
            "version": "v2",
        },
        "files": [
            {"key": "first.csv", "links": {"self": "https://example.org/first.csv"}},
            {
                "key": "second.zip",
                "links": {"download": "https://example.org/second.zip"},
            },
        ],
    }
    create_dataset_calls: list[dict] = []
    create_distribution_calls: list[dict] = []

    monkeypatch.setattr(zenodo_mod.ZenodoToDataBusMapper, "_get_record", lambda *_: record)
    monkeypatch.setattr(
        zenodo_mod,
        "sha256_tuple_for_distribution_url",
        lambda *_args, **_kwargs: ("0" * 64, 12345),
    )
    monkeypatch.setattr(
        zenodo_mod.databusclient,
        "create_distribution",
        lambda **kwargs: create_distribution_calls.append(kwargs) or kwargs,
    )
    monkeypatch.setattr(
        zenodo_mod.databusclient,
        "create_dataset",
        lambda version_id, **kwargs: (
            create_dataset_calls.append({"version_id": version_id, **kwargs})
            or {"version_id": version_id, **kwargs}
        ),
    )

    mapper = zenodo_mod.ZenodoToDataBusMapper("https://zenodo.org")
    group = utils_mod.GroupMetadata("wedowind", "Group", "Group abstract", "Group description")
    out = mapper.map_to_databus_dataset("42", group)

    assert len(create_distribution_calls) == 2
    assert create_distribution_calls[0]["cvs"]["part"] == "0"
    assert create_distribution_calls[1]["cvs"]["part"] == "1"
    assert create_distribution_calls[0]["file_format"] == "csv"
    assert create_distribution_calls[1]["file_format"] == "zip"
    assert create_distribution_calls[0]["sha256_length_tuple"] == ("0" * 64, 12345)
    assert create_distribution_calls[1]["sha256_length_tuple"] == ("0" * 64, 12345)

    assert out["title"] == "T" * 100
    assert len(out["abstract"]) == 300
    assert len(out["description"]) == 300
    assert out["license_url"] == "https://creativecommons.org/licenses/by/4.0/"
    assert create_dataset_calls[0]["version_id"].endswith("/v2")


def test_zenodo_mapper_reads_access_token_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, zenodo_mod, _checkpoint_mod = _bootstrap_mapper_imports()
    monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "token-from-env")
    mapper = zenodo_mod.ZenodoToDataBusMapper()
    assert mapper.session.headers["Authorization"] == "Bearer token-from-env"


def test_fetch_source_records_clamps_size_for_anonymous_and_authenticated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, zenodo_mod, _checkpoint_mod = _bootstrap_mapper_imports()
    captured_params: list[dict] = []

    def fake_request_json(_path: str, params: dict | None = None):
        captured_params.append(dict(params or {}))
        return {"hits": {"hits": []}}

    anon_mapper = zenodo_mod.ZenodoToDataBusMapper(access_token=None)
    monkeypatch.setattr(anon_mapper, "_request_json", fake_request_json)
    anon_mapper.fetch_source_records("community_wedowind", page=1, size=100)
    assert captured_params[-1]["size"] == 25

    auth_mapper = zenodo_mod.ZenodoToDataBusMapper(access_token="token")
    monkeypatch.setattr(auth_mapper, "_request_json", fake_request_json)
    auth_mapper.fetch_source_records("community_wedowind", page=1, size=100)
    assert captured_params[-1]["size"] == 100


def test_timestamp_state_roundtrip_and_filtering(tmp_path) -> None:
    _, zenodo_mod, checkpoint_mod = _bootstrap_mapper_imports()
    path = tmp_path / "timestamps" / "timestamp_zenodo.json"
    state = zenodo_mod.DEFAULT_TIMESTAMP_STATE.copy()
    state["community_wedowind"] = {
        "last_run_at": "2026-05-01T00:00:00+00:00",
        "last_seen_updated": "2026-05-01T10:00:00+00:00",
        "last_seen_dataset_id": "2",
        "processed_dataset_ids": ["1", "2"],
    }
    zenodo_mod.save_timestamp_state(state, path=path)
    loaded = zenodo_mod.load_timestamp_state(path=path)

    records = [
        {"id": "2", "updated": "2026-05-01T09:30:00+00:00"},
        {"id": "3", "updated": "2026-05-01T11:00:00+00:00"},
    ]
    filtered = checkpoint_mod.filter_new_datasets(
        records, loaded["community_wedowind"], overlap_hours=0
    )
    assert [r["id"] for r in filtered] == ["3"]


def test_load_source_query_params_from_json(tmp_path) -> None:
    _, zenodo_mod, _checkpoint_mod = _bootstrap_mapper_imports()
    path = tmp_path / "sources" / "sources_zenodo.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "{\n"
            '  "defaults": {\n'
            '    "group": {\n'
            '      "name": "wedowind/zenodo",\n'
            '      "title": "T",\n'
            '      "abstract": "A",\n'
            '      "description": "D"\n'
            "    }\n"
            "  },\n"
            '  "sources": {\n'
            '    "community_wedowind": {"communities": "wedowind"},\n'
            '    "subject_euroscivoc_1695": {"q": "metadata.subjects.id:\\"euroscivoc:1695\\""}\n'
            "  }\n"
            "}\n"
        ),
        encoding="utf-8",
    )
    out = zenodo_mod.load_source_query_params(path=path)
    assert out["community_wedowind"]["communities"] == "wedowind"
    assert out["subject_euroscivoc_1695"]["q"] == 'metadata.subjects.id:"euroscivoc:1695"'


def test_load_source_config_reads_group_defaults(tmp_path) -> None:
    _, zenodo_mod, _checkpoint_mod = _bootstrap_mapper_imports()
    path = tmp_path / "sources" / "sources_zenodo.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "{\n"
            '  "defaults": {\n'
            '    "group": {\n'
            '      "name": "wedowind/zenodo",\n'
            '      "title": "Zenodo Wind Energy",\n'
            '      "abstract": "A",\n'
            '      "description": "B"\n'
            "    }\n"
            "  },\n"
            '  "sources": {"community_wedowind": {"communities": "wedowind"}}\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    config = zenodo_mod.load_source_config(path=path)
    assert config["defaults"]["group"]["name"] == "wedowind/zenodo"
    assert config["defaults"]["group"]["title"] == "Zenodo Wind Energy"
    assert config["sources"]["community_wedowind"]["communities"] == "wedowind"


def test_advance_source_state_updates_checkpoint() -> None:
    _, _zenodo_mod, checkpoint_mod = _bootstrap_mapper_imports()
    source_state = {
        "last_run_at": None,
        "last_seen_updated": None,
        "last_seen_dataset_id": None,
        "processed_dataset_ids": [],
    }
    processed = [
        {"id": "3", "updated": "2026-05-01T11:00:00+00:00"},
        {"id": "4", "updated": "2026-05-01T12:00:00+00:00"},
    ]
    run_at = datetime(2026, 5, 2, 8, 0, tzinfo=UTC)
    next_state = checkpoint_mod.advance_source_state(
        source_state, processed_datasets=processed, run_at=run_at
    )
    assert next_state["last_run_at"] == "2026-05-02T08:00:00+00:00"
    assert next_state["last_seen_dataset_id"] == "4"
    assert next_state["processed_dataset_ids"][:2] == ["3", "4"]
