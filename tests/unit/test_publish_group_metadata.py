from __future__ import annotations

import pytest
from databusclient.api.deploy import BadArgumentException

from databus_manager import publish_group_metadata as mod


def test_build_distributions_single_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    def fake_create_distribution(**kwargs):
        calls.append(kwargs)
        return "dist"

    monkeypatch.setattr(mod, "create_distribution", fake_create_distribution)

    out = mod.build_distributions(
        {"distribution": [{"downloadURL": "https://example.org/file", "compression": "none"}]}
    )
    assert out == ["dist"]
    assert calls[0]["file_format"] == "txt"
    assert calls[0]["compression"] is None
    assert calls[0]["cvs"] == {}


def test_build_distributions_multi_adds_part(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(
        mod,
        "create_distribution",
        lambda **kwargs: calls.append(kwargs) or f"dist-{kwargs['cvs'].get('part','x')}",
    )
    out = mod.build_distributions(
        {"distribution": [{"downloadURL": "u1"}, {"downloadURL": "u2", "formatExtension": "zip"}]}
    )
    assert out == ["dist-0", "dist-1"]
    assert calls[0]["cvs"] == {"part": "0"}
    assert calls[1]["cvs"] == {"part": "1"}


def test_build_distributions_rejects_missing_url() -> None:
    with pytest.raises(BadArgumentException):
        mod.build_distributions({"distribution": [{}]})
