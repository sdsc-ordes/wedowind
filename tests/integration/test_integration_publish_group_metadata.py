from __future__ import annotations

from pathlib import Path

import pytest

from databus_manager import publish_group_metadata as mod


class _DummyResponse:
    def __init__(self) -> None:
        self.status_code = 201
        self.ok = True
        self.text = ""

    def raise_for_status(self) -> None:
        return None


def test_publish_builds_payload_and_posts(
    sample_catalog: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict = {}

    monkeypatch.setattr(
        mod,
        "create_distribution",
        lambda **kwargs: {"@type": "Part", "downloadURL": kwargs["url"], "cvs": kwargs["cvs"]},
    )

    def fake_create_dataset(**kwargs):
        return {"@graph": [{"@id": kwargs["version_id"]}], "distribution": kwargs["distributions"]}

    monkeypatch.setattr(mod, "create_dataset", fake_create_dataset)

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _DummyResponse()

    monkeypatch.setattr(mod.requests, "post", fake_post)

    version_file = sample_catalog / "group-zenodo" / "artifact-example-artefact-one" / "v1.0.0" / "version.jsonld"
    mod.publish(version_file, api_key="secret", register_url="https://example.org/register")

    assert captured["url"] == "https://example.org/register"
    assert captured["headers"]["X-API-KEY"] == "secret"
    assert captured["json"]["@context"] == "https://databus.openenergyplatform.org/res/context.jsonld"
