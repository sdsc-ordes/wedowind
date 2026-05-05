"""
Structured, human-oriented logs (JSON / JSONL).

Extension points:
- Add JSON Schema files under ``databus_manager/schemas/`` and validate in
  :func:`write_json` when ``validate=True``.
- Change layout (e.g. per-run subdirs) in :class:`LogWriter`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class LogWriter:
    """Writes run artifacts under ``catalog_root / .databus / logs``."""

    catalog_root: Path
    run_id: str
    entries: list[dict[str, Any]] = field(default_factory=list)

    @property
    def log_dir(self) -> Path:
        return self.catalog_root / ".databus" / "logs"

    def ensure_log_dir(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def append_publish_line(self, record: dict[str, Any]) -> None:
        """Append one JSON object to ``publish_log.jsonl`` (append-only ledger)."""
        self.ensure_log_dir()
        path = self.log_dir / "publish_log.jsonl"
        line = json.dumps(record, indent=None, ensure_ascii=False, sort_keys=False)
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def write_json(self, name: str, payload: Any, *, indent: int = 2) -> Path:
        """Write a pretty-printed JSON file (discrepancies, failures, reports)."""
        self.ensure_log_dir()
        path = self.log_dir / name
        path.write_text(
            json.dumps(payload, indent=indent, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path

    def write_run_summary_md(self, body: str) -> Path:
        """Optional Markdown companion for quick reading in GitHub."""
        self.ensure_log_dir()
        path = self.log_dir / f"run_summary_{self.run_id}.md"
        path.write_text(body, encoding="utf-8")
        return path


def empty_report_shell(*, run_id: str, catalog_root: Path) -> dict[str, Any]:
    """Template structure for a per-run report wrapper."""
    return {
        "run_id": run_id,
        "started_at": utc_now_iso(),
        "catalog_root": str(catalog_root.resolve()),
        "note": "Populate with groups/artefacts/versions/discrepancies sections when extending stubs.",
    }
