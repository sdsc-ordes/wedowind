#!/usr/bin/env python3
"""
Publish a catalog version with explicit group metadata via databusclient API.

Why this script:
- `databusclient deploy` CLI sets artifact/version metadata from options.
- Group metadata is only available through `create_dataset(...)` Python args
  (`group_title`, `group_abstract`, `group_description`).

This script reads:
- `catalog/<group>/group-metadata.jsonld`
- `catalog/<group>/<artifact-dir>/v<semver>/version.jsonld`

And publishes one version to OEP `/api/register`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from databusclient.api.deploy import BadArgumentException, create_dataset, create_distribution

from databus_manager.handle_jsonld import get_graph_node, load_json
from databus_manager.load_env import load_dotenv_if_available
from databus_manager.parse import build_publish_group_parser

DEFAULT_CONTEXT = "https://databus.openenergyplatform.org/res/context.jsonld"
DEFAULT_REGISTER_URL = "https://databus.openenergyplatform.org/api/register"


class RegisterPublishError(Exception):
    """Register endpoint returned a non-success status (response body often contains SHACL errors)."""

    def __init__(self, status_code: int, response_text: str) -> None:
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(f"HTTP {status_code}")


def _graph_node(doc: dict[str, Any], expected_type: str) -> dict[str, Any]:
    try:
        return get_graph_node(doc, expected_type)
    except ValueError as err:
        raise BadArgumentException(str(err)) from err


def build_distributions(version_node: dict[str, Any]) -> list[str]:
    parts = version_node.get("distribution")
    if not isinstance(parts, list) or not parts:
        raise BadArgumentException("Version node must contain a non-empty distribution list.")

    out: list[str] = []
    single = len(parts) == 1
    for idx, part in enumerate(parts):
        url = part.get("downloadURL")
        if not isinstance(url, str) or not url:
            raise BadArgumentException(f"Distribution part {idx} has no valid downloadURL.")

        file_format = part.get("formatExtension")
        if not isinstance(file_format, str) or not file_format:
            file_format = "txt"

        compression = part.get("compression")
        if not isinstance(compression, str) or compression.lower() in ("", "none"):
            compression = None

        cvs: dict[str, str] = {} if single else {"part": str(idx)}
        out.append(
            create_distribution(
                url=url,
                cvs=cvs,
                file_format=file_format,
                compression=compression,
            )
        )
    return out


def publish(version_file: Path, api_key: str, register_url: str) -> None:
    version_doc = load_json(version_file)
    version_node = _graph_node(version_doc, "Version")

    group_file = version_file.parents[2] / "group-metadata.jsonld"
    if not group_file.is_file():
        raise BadArgumentException(f"Group metadata missing at {group_file}")
    group_doc = load_json(group_file)
    group_node = _graph_node(group_doc, "Group")

    distributions = build_distributions(version_node)
    dataset = create_dataset(
        version_id=version_node["@id"],
        title=version_node["title"],
        abstract=version_node["abstract"],
        description=version_node.get("description") or "NA",
        license_url=version_node["license"],
        distributions=distributions,
        group_title=group_node["title"],
        group_abstract=group_node["abstract"],
        group_description=group_node["description"],
    )
    dataset["@context"] = version_doc.get("@context", DEFAULT_CONTEXT)

    resp = requests.post(
        register_url,
        json=dataset,
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        timeout=120,
    )
    if not resp.ok:
        raise RegisterPublishError(resp.status_code, resp.text)


def main() -> int:
    load_dotenv_if_available()
    args = build_publish_group_parser().parse_args()

    api_key = args.api_key or os.getenv("DATABUS_API_KEY")
    if not api_key:
        raise SystemExit("Missing API key: pass --api-key or set DATABUS_API_KEY.")

    version_path = Path(args.version_file)
    if not version_path.is_file():
        raise SystemExit(f"Version file not found: {version_path}")

    try:
        publish(version_path, api_key, args.register_url)
    except RegisterPublishError as err:
        print(f"[publish] failed: {version_path}", flush=True)
        print(err.response_text, flush=True)
        raise SystemExit(1) from err
    print(f"[publish] published: {version_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
