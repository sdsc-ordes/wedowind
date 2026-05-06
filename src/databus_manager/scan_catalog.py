from pathlib import Path

from databus_manager.handle_jsonld import (
    load_json,
    get_graph_node,
    version_id_to_group_id,
    version_id_to_artefact_id,
)

from databus_manager.objects.metadata import CatalogVersionRef

# Version directories are ``v<semver>/`` only (e.g. ``v1.2.0/``).
_VERSION_JSONLD_GLOB = "group-*/artifact-*/v*/version.jsonld"


def _artifact_metadata_file(artifact_dir: Path) -> Path | None:
    candidate = artifact_dir / "artifact-metadata.jsonld"
    return candidate if candidate.is_file() else None


def _discovered_version_files(catalog_root: Path) -> list[Path]:
    seen: dict[str, Path] = {}
    for vf in catalog_root.glob(_VERSION_JSONLD_GLOB):
        seen[str(vf.resolve())] = vf
    return sorted(seen.values(), key=lambda p: str(p))


def scan_catalog(catalog_root: Path) -> list[CatalogVersionRef]:
    """Scan catalog for ``v<semver>/version.jsonld`` and resolve group + artifact metadata paths."""
    entries: list[CatalogVersionRef] = []
    for version_file in _discovered_version_files(catalog_root):
        version_doc = load_json(version_file)
        version_node = get_graph_node(version_doc, "Version")
        version_id = str(version_node.get("@id", "")).strip()
        if not version_id:
            continue
        group_file = version_file.parents[2] / "group-metadata.jsonld"
        artifact_file = _artifact_metadata_file(version_file.parents[1])
        if not group_file.is_file() or artifact_file is None:
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
