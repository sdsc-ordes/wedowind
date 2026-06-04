from __future__ import annotations

import pytest

from mappers.oep.oep_defaults import OepDefaults
from mappers.zenodo.oep_mapper import ZenodoToOepMapper


def test_zenodo_oep_mapper_builds_resources_and_dataset(monkeypatch: pytest.MonkeyPatch) -> None:
    """Zenodo mapper produces OEMetadata with licenses, resources, and DOI."""
    record = {
        "id": 99,
        "created": "2024-06-01T10:00:00+00:00",
        "metadata": {
            "title": "Wind dataset",
            "description": "<p>About wind</p>",
            "license": {"id": "cc-by-4.0"},
            "keywords": ["wind"],
            "creators": [{"name": "Ada Lovelace", "affiliation": "Analytical Engine"}],
            "doi": "10.5281/zenodo.123",
        },
        "files": [
            {"key": "data.csv", "links": {"self": "https://zenodo.org/files/data.csv"}},
        ],
    }
    monkeypatch.setattr(
        "mappers.zenodo.client.ZenodoClient.get_record",
        lambda self, _id: record,
    )
    oep = OepDefaults(table_prefix="wd_", infer_schema=False)
    doc = ZenodoToOepMapper(source_key="test_src").map_to_oemetadata("99", oep)
    assert doc["title"] == "Wind dataset"
    assert len(doc["resources"]) == 1
    assert doc["resources"][0]["licenses"][0]["name"] == "CC-BY-4.0"
    assert doc["@id"] == "https://doi.org/10.5281/zenodo.123"


def test_zenodo_oep_metadata_passes_omi_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mapped Zenodo OEMetadata passes OMI schema validation."""
    record = {
        "id": 1,
        "metadata": {"title": "T", "description": "D", "license": {"id": "cc0-1.0"}},
        "files": [{"key": "a.txt", "links": {"download": "https://example.org/a.txt"}}],
    }
    monkeypatch.setattr(
        "mappers.zenodo.client.ZenodoClient.get_record",
        lambda self, _id: record,
    )
    from mappers.oep.api import validate_oemetadata

    doc = ZenodoToOepMapper(source_key="s").map_to_oemetadata("1", OepDefaults())
    validate_oemetadata(doc)
