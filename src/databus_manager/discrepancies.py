"""
Compare catalog JSON-LD with metadata fetched from Databus (template stubs).

Extension points:
- Implement remote fetch via SPARQL (``databus_manager.config.SPARQL_URL``) or HTTP
  GET on resource ``@id`` IRIs if your server supports content negotiation.
- Compare graphs canonically (e.g. ``pyld`` expansion + sorted n-quads, or ``rdflib``
  isomorphism) — avoid naive JSON string equality on JSON-LD.
- Write rich records to ``discrepancies.json`` via :class:`databus_manager.logging_utils.LogWriter`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from databus_manager.logging_utils import LogWriter


def check_catalog_vs_remote(
    catalog_root: Path,
    log: LogWriter,
) -> list[dict[str, Any]]:
    """
    For entities previously published (see publish ledger), fetch remote state and diff.

    Stub: returns an empty list and documents intended behaviour.
    """
    stub_note = (
        "Implement check_catalog_vs_remote: load publish_log.jsonl keys, "
        "fetch each entity from Databus, diff against local JSON-LD files."
    )
    report = {
        "generated_by": "databus_manager.discrepancies",
        "discrepancies": [],
        "stub_note": stub_note,
    }
    log.write_json("discrepancies.json", report)
    return []
