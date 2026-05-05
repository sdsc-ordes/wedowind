from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from databus_manager.objects.metadata import (
    ArtefactMetadata,
    GroupMetadata,
    VersionMetadata,
)
from databus_manager.sparql import sparql_select

def _coalesce_detection_timestamp(override: str | None) -> str:
    if override is not None:
        return override
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _optional_metadata_group(row: dict[str, Any] | None, group_id: str) -> GroupMetadata | None:
    if not row:
        return None
    return GroupMetadata.from_remote_dict(group_id, row)


def _optional_metadata_artefact(row: dict[str, Any] | None, artefact_id: str) -> ArtefactMetadata | None:
    if not row:
        return None
    return ArtefactMetadata.from_remote_dict(artefact_id, row)


def _optional_metadata_version(row: dict[str, Any] | None, version_id: str) -> VersionMetadata | None:
    if not row:
        return None
    return VersionMetadata.from_remote_dict(version_id, row)

def fetch_remote_version(version_id: str, sparql_url: str) -> dict[str, Any] | None:
    query = f"""
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX databus: <https://dataid.dbpedia.org/databus#>

    SELECT ?title ?abstract ?description ?license ?downloadURL ?formatExtension ?compression
    WHERE {{
      GRAPH ?g {{
        BIND(<{version_id}> AS ?dataset)
        ?dataset dcat:distribution ?part .
        OPTIONAL {{ ?dataset dct:title ?title . }}
        OPTIONAL {{ ?dataset dct:abstract ?abstract . }}
        OPTIONAL {{ ?dataset dct:description ?description . }}
        OPTIONAL {{ ?dataset dct:license ?license . }}
        OPTIONAL {{ ?part dcat:downloadURL ?downloadURL . }}
        OPTIONAL {{ ?part databus:formatExtension ?formatExtension . }}
        OPTIONAL {{ ?part databus:compression ?compression . }}
      }}
    }}
    """
    rows = sparql_select(sparql_url, query)
    if not rows:
        return None

    first = rows[0]
    distribution: list[dict[str, Any]] = []
    for row in rows:
        dl = row.get("downloadURL", "")
        if not dl:
            continue
        distribution.append(
            {
                "@type": "Part",
                "formatExtension": row.get("formatExtension", "") or "txt",
                "compression": row.get("compression", "") or "none",
                "downloadURL": dl,
            }
        )
    if not distribution:
        return None
    return {
        "@id": version_id,
        "@type": "Version",
        "title": first.get("title", ""),
        "abstract": first.get("abstract", ""),
        "description": first.get("description", ""),
        "license": first.get("license", ""),
        "distribution": distribution,
    }


def fetch_remote_group(group_id: str, sparql_url: str) -> dict[str, Any] | None:
    query = f"""
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX databus: <https://dataid.dbpedia.org/databus#>

    SELECT ?title ?abstract ?description
    WHERE {{
      GRAPH ?g {{
        BIND(<{group_id}> AS ?group)
        ?group rdf:type databus:Group .
        OPTIONAL {{ ?group dct:title ?title . }}
        OPTIONAL {{ ?group dct:abstract ?abstract . }}
        OPTIONAL {{ ?group dct:description ?description . }}
      }}
    }}
    LIMIT 1
    """
    rows = sparql_select(sparql_url, query)
    if not rows:
        return None
    row = rows[0]
    return {
        "@id": group_id,
        "@type": "Group",
        "title": row.get("title", ""),
        "abstract": row.get("abstract", ""),
        "description": row.get("description", ""),
    }


def fetch_remote_artefact(artefact_id: str, sparql_url: str) -> dict[str, Any] | None:
    query = f"""
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX databus: <https://dataid.dbpedia.org/databus#>

    SELECT ?title ?abstract ?description
    WHERE {{
      GRAPH ?g {{
        BIND(<{artefact_id}> AS ?artefact)
        ?artefact rdf:type databus:Artifact .
        OPTIONAL {{ ?artefact dct:title ?title . }}
        OPTIONAL {{ ?artefact dct:abstract ?abstract . }}
        OPTIONAL {{ ?artefact dct:description ?description . }}
      }}
    }}
    LIMIT 1
    """
    rows = sparql_select(sparql_url, query)
    if not rows:
        return None
    row = rows[0]
    return {
        "@id": artefact_id,
        "@type": "Artifact",
        "title": row.get("title", ""),
        "abstract": row.get("abstract", ""),
        "description": row.get("description", ""),
    }