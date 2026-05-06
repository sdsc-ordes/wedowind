from __future__ import annotations

import json
from pathlib import Path

import pytest

from databus_manager.objects.logs import (
    DiscrepancyLogEntry,
    PublishingLedgerEntry,
    append_jsonl,
    iter_discrepancy_log,
    iter_publishing_ledger,
    publishing_ledger_index_by_entity_id,
)


def test_discrepancy_log_entry_validates() -> None:
    row = DiscrepancyLogEntry(
        timestamp="2026-01-01T00:00:00+00:00",
        entity_id="g",
        entity_type="group",
        metadata_field="title",
        remote_value="r",
        local_value="l",
    )
    assert row.to_dict()["entity_type"] == "group"


def test_discrepancy_log_entry_rejects_invalid_field() -> None:
    with pytest.raises(ValueError):
        DiscrepancyLogEntry(
            timestamp="2026-01-01T00:00:00+00:00",
            entity_id="g",
            entity_type="group",
            metadata_field="license",
            remote_value="r",
            local_value="l",
        )


def test_iterators_skip_bad_lines_and_parse_legacy(tmp_path: Path) -> None:
    discrepancy_path = tmp_path / "disc.jsonl"
    append_jsonl(
        discrepancy_path,
        DiscrepancyLogEntry(
            timestamp="2026-01-01T00:00:00+00:00",
            entity_id="g",
            entity_type="group",
            metadata_field="title",
            remote_value="r",
            local_value="l",
        ).to_dict(),
    )
    with discrepancy_path.open("a", encoding="utf-8") as f:
        f.write("not-json\n")
    rows = list(iter_discrepancy_log(discrepancy_path))
    assert len(rows) == 1

    ledger_path = tmp_path / "ledger.jsonl"
    append_jsonl(ledger_path, {"ts": "2026-01-01T00:00:00+00:00", "version_id": "v1"})
    append_jsonl(
        ledger_path,
        PublishingLedgerEntry(
            timestamp="2026-01-02T00:00:00+00:00", entity_id="v2", entity_type="version"
        ).to_dict(),
    )
    parsed = list(iter_publishing_ledger(ledger_path))
    assert {x.entity_id for x in parsed} == {"v1", "v2"}
    index = publishing_ledger_index_by_entity_id(ledger_path)
    assert set(index.keys()) == {"v1", "v2"}
