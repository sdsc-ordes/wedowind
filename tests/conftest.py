from __future__ import annotations

import json
from pathlib import Path

import pytest

from databus_manager.load_env import load_dotenv_if_available

load_dotenv_if_available()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@pytest.fixture
def sample_catalog(tmp_path: Path) -> Path:
    catalog = tmp_path / "catalog"
    group_dir = catalog / "group-zenodo"
    artefact_dir = group_dir / "artifact-example-artefact-one"
    version_dir = artefact_dir / "version-1"

    _write_json(
        group_dir / "group-metadata.jsonld",
        {
            "@context": "https://databus.openenergyplatform.org/res/context.jsonld",
            "@graph": [
                {
                    "@id": "https://databus.openenergyplatform.org/wedowind/zenodo",
                    "@type": "Group",
                    "title": "Zenodo",
                    "abstract": "Group abstract",
                    "description": "Group description",
                }
            ],
        },
    )
    _write_json(
        artefact_dir / "artefact-metadata.jsonld",
        {
            "@context": "https://databus.openenergyplatform.org/res/context.jsonld",
            "@graph": [
                {
                    "@id": "https://databus.openenergyplatform.org/wedowind/zenodo/example-artefact-one",
                    "@type": "Artifact",
                    "title": "Artefact one",
                    "abstract": "Artefact abstract",
                    "description": "Artefact description",
                }
            ],
        },
    )
    _write_json(
        version_dir / "version.jsonld",
        {
            "@context": "https://databus.openenergyplatform.org/res/context.jsonld",
            "@graph": [
                {
                    "@id": "https://databus.openenergyplatform.org/wedowind/zenodo/example-artefact-one/v1.0.0",
                    "@type": "Version",
                    "title": "v1.0.0",
                    "abstract": "Version abstract",
                    "description": "Version description",
                    "license": "https://dalicc.net/licenselibrary/CC-BY-4.0",
                    "distribution": [
                        {
                            "@type": "Part",
                            "formatExtension": "zip",
                            "compression": "none",
                            "downloadURL": "https://doi.org/10.5281/zenodo.15471425",
                        }
                    ],
                }
            ],
        },
    )
    return catalog
