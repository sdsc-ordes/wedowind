from pathlib import Path
from typing import Any

from databus_manager.handle_jsonld import (
    load_json, 
    get_graph_node, 
    version_id_to_group_id, 
    version_id_to_artefact_id
)

from databus_manager.objects.metadata import CatalogVersionRef

def scan_catalog(catalog_root: Path) -> list[CatalogVersionRef]:
    """Scan catalog for version files and resolve sibling group + artefact metadata paths."""
    entries: list[CatalogVersionRef] = []
    for version_file in sorted(catalog_root.glob("group-*/artefacts-*/version-*/version.jsonld")):
        version_doc = load_json(version_file)
        version_node = get_graph_node(version_doc, "Version")
        version_id = str(version_node.get("@id", "")).strip()
        if not version_id:
            continue
        group_file = version_file.parents[2] / "group-metadata.jsonld"
        artifact_file = version_file.parents[1] / "artefact-metadata.jsonld"
        if not group_file.is_file() or not artifact_file.is_file():
            continue
        entries.append(
            CatalogVersionRef(
                version_file=version_file,
                group_file=group_file,
                artifact_file=artifact_file,
                version_id=version_id,
                group_id=version_id_to_group_id(version_id),
                artifact_id=version_id_to_artefact_id(version_id),
            )
        )
    return entries

