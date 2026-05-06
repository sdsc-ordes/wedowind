"""Domain objects: typed metadata and schema-backed logs."""

from databus_manager.objects.logs import (
    DiscrepancyLogEntry,
    METADATA_FIELDS_BY_ENTITY,
    PublishingEntry,
    append_jsonl,
    ensure_metadata_field,
    iter_discrepancy_log,
    iter_publishings,
    publishings_index_by_entity_id,
    schemas_dir,
    validate_discrepancy,
    validate_publishing,
)
from databus_manager.objects.metadata import (
    ArtefactMetadata,
    CatalogVersionRef,
    GroupMetadata,
    VersionMetadata,
)
from databus_manager.handle_jsonld import (
    get_graph_node,
    load_json,
    version_id_to_artefact_id,
    version_id_to_group_id,
    write_json,
)

__all__ = [
    "ArtefactMetadata",
    "CatalogVersionRef",
    "DiscrepancyLogEntry",
    "GroupMetadata",
    "METADATA_FIELDS_BY_ENTITY",
    "PublishingEntry",
    "VersionMetadata",
    "append_jsonl",
    "scan_catalog",
    "ensure_metadata_field",
    "get_graph_node",
    "iter_discrepancy_log",
    "iter_publishings",
    "load_json",
    "publishings_index_by_entity_id",
    "schemas_dir",
    "validate_discrepancy",
    "validate_publishing",
    "version_id_to_artefact_id",
    "version_id_to_group_id",
    "write_json",
]


def __getattr__(name: str):
    if name == "scan_catalog":
        from databus_manager.scan_catalog import scan_catalog as _scan_catalog

        return _scan_catalog
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
