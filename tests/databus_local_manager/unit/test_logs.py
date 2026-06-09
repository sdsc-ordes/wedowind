from __future__ import annotations

import json
from pathlib import Path

from databus_local_manager.logs import (
    PublishingEntry,
    append_jsonl,
    iter_publishings,
    publishings_index_by_entity_id,
)


def test_iter_publishings_skips_bad_lines(tmp_path: Path) -> None:
    publishings_path = tmp_path / "publishings.jsonl"
    append_jsonl(
        publishings_path,
        PublishingEntry(
            timestamp="2026-01-01T00:00:00+00:00", entity_id="v1", entity_type="version"
        ).to_dict(),
    )
    append_jsonl(
        publishings_path,
        PublishingEntry(
            timestamp="2026-01-02T00:00:00+00:00", entity_id="v2", entity_type="version"
        ).to_dict(),
    )
    with publishings_path.open("a", encoding="utf-8") as f:
        f.write("not-json\n")
        f.write(json.dumps({"version_id": "legacy-only"}) + "\n")

    parsed = list(iter_publishings(publishings_path))
    assert {x.entity_id for x in parsed} == {"v1", "v2"}
    index = publishings_index_by_entity_id(publishings_path)
    assert set(index.keys()) == {"v1", "v2"}
