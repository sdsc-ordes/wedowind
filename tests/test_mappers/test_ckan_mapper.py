from __future__ import annotations

import importlib
import sys
import types


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
    sys.modules.setdefault("ckanapi", types.SimpleNamespace(RemoteCKAN=object))
    utils_mod = importlib.import_module("mappers.utils")
    ckan_mod = importlib.import_module("mappers.ckan.mapper")
    return utils_mod, ckan_mod


def _stub_ckan_resource_checksum(monkeypatch, ckan_mod):
    """Avoid real HTTP when mapping CKAN resources (SHA-256 streaming)."""
    monkeypatch.setattr(
        ckan_mod,
        "sha256_tuple_for_distribution_url",
        lambda *args, **kwargs: ("0" * 64, 12345),
    )


def test_ckan_mapper_uses_sanitized_text_fields(monkeypatch) -> None:
    utils_mod, ckan_mod = _bootstrap_mapper_imports()
    _stub_ckan_resource_checksum(monkeypatch, ckan_mod)

    dataset_payload = {
        "name": "artifact-name",
        "version": "v1",
        "title": "t" * 110,
        "topic": "a" * 350,
        "notes": "d" * 360,
        "license_id": "https://example.org/license",
        "resources": [
            {
                "url": "https://example.org/file.csv",
                "resource_type": "data",
                "format": "csv",
            }
        ],
    }

    class FakeAction:
        @staticmethod
        def package_show(id: str):
            assert id == "dataset-id"
            return dataset_payload

    class FakeRemoteCKAN:
        def __init__(self, _url: str):
            self.action = FakeAction()

    dist_calls: list[dict] = []
    dataset_calls: list[dict] = []

    def fake_create_distribution(**kwargs):
        dist_calls.append(kwargs)
        return {"distribution": kwargs}

    def fake_create_dataset(version_id, **kwargs):
        dataset_calls.append({"version_id": version_id, **kwargs})
        return {"version_id": version_id, **kwargs}

    monkeypatch.setattr(ckan_mod, "RemoteCKAN", FakeRemoteCKAN)
    monkeypatch.setattr(ckan_mod.databusclient, "create_distribution", fake_create_distribution)
    monkeypatch.setattr(ckan_mod.databusclient, "create_dataset", fake_create_dataset)

    mapper = ckan_mod.CKANToDataBusMapper("https://example.org")
    group = utils_mod.GroupMetadata(
        "wedowind", "group title", "group abstract", "group description"
    )
    out = mapper.map_to_databus_dataset("dataset-id", group)

    assert out["title"] == "t" * 100
    assert out["abstract"] == "a" * 300
    assert out["description"] == "d" * 300
    assert len(dist_calls) == 1
    assert dist_calls[0]["sha256_length_tuple"] == ("0" * 64, 12345)
    assert dataset_calls[0]["title"] == "t" * 100


def test_ckan_mapper_sanitizes_resource_format_with_spaces_for_databus(
    monkeypatch,
) -> None:
    """CKAN format strings like 'SHP ZIP' must not produce spaces inside Databus CV/IRI segments."""
    utils_mod, ckan_mod = _bootstrap_mapper_imports()
    _stub_ckan_resource_checksum(monkeypatch, ckan_mod)

    dataset_payload = {
        "name": "ghana-wind",
        "version": "v1",
        "title": "T",
        "topic": "A",
        "notes": "D",
        "license_id": "https://example.org/license",
        "resources": [
            {
                "url": "https://example.org/a.zip",
                "resource_type": "Doc Umentation",
                "format": "SHP ZIP",
            },
            {
                "url": "https://example.org/b.csv",
                "resource_type": "data",
                "format": "csv",
            },
        ],
    }

    class FakeAction:
        @staticmethod
        def package_show(id: str):
            return dataset_payload

    class FakeRemoteCKAN:
        def __init__(self, _url: str):
            self.action = FakeAction()

    dist_calls: list[dict] = []

    def fake_create_distribution(**kwargs):
        dist_calls.append(kwargs)
        return {"distribution": kwargs}

    monkeypatch.setattr(ckan_mod, "RemoteCKAN", FakeRemoteCKAN)
    monkeypatch.setattr(ckan_mod.databusclient, "create_distribution", fake_create_distribution)
    monkeypatch.setattr(ckan_mod.databusclient, "create_dataset", lambda *a, **k: {})

    mapper = ckan_mod.CKANToDataBusMapper("https://example.org")
    group = utils_mod.GroupMetadata("wedowind/wbg", "t", "a", "d")
    mapper.map_to_databus_dataset("ghana-wind", group)

    assert len(dist_calls) == 2
    assert dist_calls[0]["file_format"] == "shp-zip"
    assert dist_calls[0]["cvs"]["type"] == "doc-umentation"
    assert dist_calls[1]["file_format"] == "csv"


def test_ckan_license_id_short_code_mapped_to_iri(monkeypatch) -> None:
    """Databus rejects bare CKAN registry ids like CC0-1.0; map to a proper license IRI."""
    utils_mod, ckan_mod = _bootstrap_mapper_imports()
    _stub_ckan_resource_checksum(monkeypatch, ckan_mod)

    dataset_payload = {
        "name": "ds",
        "version": "v1",
        "title": "T",
        "topic": "A",
        "notes": "D",
        "license_id": "CC0-1.0",
        "resources": [
            {
                "url": "https://example.org/f.csv",
                "resource_type": "data",
                "format": "csv",
            }
        ],
    }

    class FakeAction:
        @staticmethod
        def package_show(id: str):
            return dataset_payload

    class FakeRemoteCKAN:
        def __init__(self, _url: str):
            self.action = FakeAction()

    dataset_calls: list[dict] = []

    def fake_create_dataset(version_id, **kwargs):
        dataset_calls.append({"version_id": version_id, **kwargs})
        return kwargs

    monkeypatch.setattr(ckan_mod, "RemoteCKAN", FakeRemoteCKAN)
    monkeypatch.setattr(
        ckan_mod.databusclient,
        "create_distribution",
        lambda **kwargs: kwargs,
    )
    monkeypatch.setattr(ckan_mod.databusclient, "create_dataset", fake_create_dataset)

    mapper = ckan_mod.CKANToDataBusMapper("https://example.org")
    group = utils_mod.GroupMetadata("g", "t", "a", "d")
    mapper.map_to_databus_dataset("ds", group)

    assert dataset_calls[0]["license_url"] == "https://creativecommons.org/publicdomain/zero/1.0/"


def test_ckan_license_prefers_http_license_url_over_short_license_id(
    monkeypatch,
) -> None:
    utils_mod, ckan_mod = _bootstrap_mapper_imports()
    _stub_ckan_resource_checksum(monkeypatch, ckan_mod)
    dataset_payload = {
        "name": "ds",
        "version": "v1",
        "title": "T",
        "topic": "A",
        "notes": "D",
        "license_id": "CC0-1.0",
        "license_url": "https://example.org/custom-license",
        "resources": [
            {
                "url": "https://example.org/f.csv",
                "resource_type": "data",
                "format": "csv",
            }
        ],
    }

    class FakeAction:
        @staticmethod
        def package_show(id: str):
            return dataset_payload

    class FakeRemoteCKAN:
        def __init__(self, _url: str):
            self.action = FakeAction()

    dataset_calls: list[dict] = []

    def fake_create_dataset(version_id, **kwargs):
        dataset_calls.append(kwargs)
        return kwargs

    monkeypatch.setattr(ckan_mod, "RemoteCKAN", FakeRemoteCKAN)
    monkeypatch.setattr(
        ckan_mod.databusclient,
        "create_distribution",
        lambda **kwargs: kwargs,
    )
    monkeypatch.setattr(ckan_mod.databusclient, "create_dataset", fake_create_dataset)

    mapper = ckan_mod.CKANToDataBusMapper("https://example.org")
    group = utils_mod.GroupMetadata("g", "t", "a", "d")
    mapper.map_to_databus_dataset("ds", group)
    assert dataset_calls[0]["license_url"] == "https://example.org/custom-license"


def test_ckan_mapper_coerces_none_resource_type_for_distributions(monkeypatch) -> None:
    utils_mod, ckan_mod = _bootstrap_mapper_imports()
    _stub_ckan_resource_checksum(monkeypatch, ckan_mod)
    dataset_payload = {
        "name": "ds",
        "version": "v1",
        "title": "T",
        "topic": "A",
        "notes": "D",
        "license_id": "https://example.org/license",
        "resources": [
            {
                "url": "https://example.org/f.csv",
                "resource_type": None,
                "format": "CSV",
            },
        ],
    }

    class FakeAction:
        @staticmethod
        def package_show(id: str):
            return dataset_payload

    class FakeRemoteCKAN:
        def __init__(self, _url: str):
            self.action = FakeAction()

    dist_calls: list[dict] = []

    def fake_create_distribution(**kwargs):
        dist_calls.append(kwargs)
        return kwargs

    monkeypatch.setattr(ckan_mod, "RemoteCKAN", FakeRemoteCKAN)
    monkeypatch.setattr(ckan_mod.databusclient, "create_distribution", fake_create_distribution)
    monkeypatch.setattr(
        ckan_mod.databusclient,
        "create_dataset",
        lambda version_id, **kwargs: kwargs,
    )

    mapper = ckan_mod.CKANToDataBusMapper("https://example.org")
    group = utils_mod.GroupMetadata("wedowind/g", "t", "a", "d")
    mapper.map_to_databus_dataset("ds", group)

    assert dist_calls[0]["cvs"]["type"] == "data"
    assert dist_calls[0]["file_format"] == "csv"


def test_ckan_mapper_multi_zip_resources_get_distinct_part_cv(monkeypatch) -> None:
    utils_mod, ckan_mod = _bootstrap_mapper_imports()
    _stub_ckan_resource_checksum(monkeypatch, ckan_mod)
    dataset_payload = {
        "name": "peshawar-annexes",
        "version": "v1",
        "title": "T",
        "topic": "A",
        "notes": "D",
        "license_id": "https://example.org/license",
        "resources": [
            {
                "url": "https://example.org/a.zip",
                "resource_type": "data",
                "format": "ZIP",
            },
            {
                "url": "https://example.org/b.zip",
                "resource_type": "data",
                "format": "ZIP",
            },
        ],
    }

    class FakeAction:
        @staticmethod
        def package_show(id: str):
            return dataset_payload

    class FakeRemoteCKAN:
        def __init__(self, _url: str):
            self.action = FakeAction()

    dist_calls: list[dict] = []

    def fake_create_distribution(**kwargs):
        dist_calls.append(kwargs)
        return kwargs

    monkeypatch.setattr(ckan_mod, "RemoteCKAN", FakeRemoteCKAN)
    monkeypatch.setattr(ckan_mod.databusclient, "create_distribution", fake_create_distribution)
    monkeypatch.setattr(
        ckan_mod.databusclient,
        "create_dataset",
        lambda version_id, **kwargs: kwargs,
    )

    mapper = ckan_mod.CKANToDataBusMapper("https://example.org")
    group = utils_mod.GroupMetadata("wedowind/g", "t", "a", "d")
    mapper.map_to_databus_dataset("ds", group)

    assert len(dist_calls) == 2
    assert dist_calls[0]["cvs"] == {"type": "data", "part": "0"}
    assert dist_calls[1]["cvs"] == {"type": "data", "part": "1"}
