"""
CLI orchestration: groups → artefacts → versions → discrepancies → logs.

Default is **dry run** (no HTTP). Pass ``--apply`` to perform real registration
once :func:`register_*` functions are implemented and ``DATABUS_API_KEY`` is set.
"""

from __future__ import annotations

import argparse
import os
import uuid
from pathlib import Path
from typing import Any

from databus_manager import artefacts, discrepancies, groups, versions
from databus_manager.logging_utils import LogWriter, empty_report_shell, utc_now_iso
from databus_manager import config


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m databus_manager",
        description="Sync catalog JSON-LD to Open Energy Platform Databus (template).",
    )
    p.add_argument(
        "--catalog",
        type=Path,
        default=Path(config.DEFAULT_CATALOG),
        help=f"Catalog root (default: {config.DEFAULT_CATALOG})",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Attempt real /api/register calls (requires implementing stubs and DATABUS_API_KEY).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    catalog_root: Path = args.catalog
    dry_run = not args.apply
    api_key = os.environ.get("DATABUS_API_KEY")
    run_id = f"{utc_now_iso()}-{uuid.uuid4().hex[:8]}"

    if not catalog_root.is_dir():
        print(f"Catalog not found: {catalog_root}", flush=True)
        return 1

    log = LogWriter(catalog_root=catalog_root, run_id=run_id)
    log.ensure_log_dir()

    report: dict[str, Any] = empty_report_shell(run_id=run_id, catalog_root=catalog_root)
    report["config"] = {
        "register_url": config.REGISTER_URL,
        "context_url": config.CONTEXT_URL,
        "sparql_url": config.SPARQL_URL,
        "dry_run": dry_run,
        "api_key_set": bool(api_key),
    }

    tree: list[dict[str, Any]] = []
    for gdir in groups.find_group_dirs(catalog_root):
        gout = groups.register_group(gdir, api_key=api_key, dry_run=dry_run)
        gnode = {"group": gdir.name, "register": gout, "artefacts": []}
        for adir in artefacts.find_artefact_dirs(gdir):
            aout = artefacts.register_artefact(adir, api_key=api_key, dry_run=dry_run)
            anode = {"artefact": adir.name, "register": aout, "versions": []}
            for vdir in versions.find_version_dirs(adir):
                vout = versions.register_version(vdir, api_key=api_key, dry_run=dry_run)
                anode["versions"].append({"version_dir": vdir.name, "register": vout})
            gnode["artefacts"].append(anode)
        tree.append(gnode)

    report["discovery"] = {"groups": tree}
    discrepancies.check_catalog_vs_remote(catalog_root, log)

    log.write_json(f"run_report_{run_id}.json", report)
    log.write_json(
        "failed_upload.json",
        {
            "run_id": run_id,
            "entries": [],
            "note": (
                "Extend databus_manager.cli (or register_* callers) to append here when a version "
                "already exists on Databus, HTTP errors occur, or validation fails before POST."
            ),
        },
    )

    summary_lines = [
        f"# Databus sync run `{run_id}`",
        "",
        f"- Catalog: `{catalog_root}`",
        f"- Dry run: **{dry_run}**",
        f"- API key present: **{bool(api_key)}**",
        f"- Register URL: {config.REGISTER_URL}",
        "",
        "## Discovered tree",
        "",
        f"Groups loaded: **{len(tree)}**",
        "",
        "See JSON: `catalog/.databus/logs/run_report_*.json` and `discrepancies.json`.",
    ]
    log.write_run_summary_md("\n".join(summary_lines) + "\n")

    out = log.log_dir / f"run_report_{run_id}.json"
    print(f"Wrote {out}", flush=True)
    return 0
