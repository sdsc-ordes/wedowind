"""Construct OEMetadata 2.0 documents from external source records."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from mappers.oep.oep_defaults import DEFAULT_OEP_CONTEXT, OepDefaults
from mappers.oep.oep_table import OepTable
from mappers.oep.sanitize import sanitize_oep_identifier
from mappers.oep.oemetadata import (
    OemetadataContext,
    OemetadataContributor,
    OemetadataDialect,
    OemetadataLicense,
    OemetadataResource,
    OemetadataSource,
)


class OemetadataBuilder:
    """Build OEMetadata dataset and resource documents.

    Stateless helper used by source mappers to assemble OEMetadata 2.0
    dataset and resource objects from upstream records.

    Attributes
    ----------
    OEP_BASE_URL : str
        Base URL for OEP dataedit resource ``path`` values.
    """

    OEP_BASE_URL = "https://openenergyplatform.org"

    @staticmethod
    def normalize_plain_text(value: str | None) -> str:
        """Strip HTML-like tags and collapse whitespace.

        Parameters
        ----------
        value : str or None
            Raw text that may contain HTML markup.

        Returns
        -------
        str
            Plain text with tags removed and whitespace normalized; empty
            string when ``value`` is falsy.
        """
        if not value:
            return ""
        no_html = re.sub(r"<[^>]+>", " ", str(value))
        return " ".join(no_html.split())

    @staticmethod
    def parse_publication_date(value: str | None) -> str | None:
        """Normalize a timestamp or date string to ISO 8601 ``YYYY-MM-DD``.

        Parameters
        ----------
        value : str or None
            Date or datetime string from an upstream source.

        Returns
        -------
        str or None
            ISO date string, or ``None`` when ``value`` cannot be parsed.
        """
        if not value:
            return None
        raw = str(value).strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(raw.replace(" ", "T", 1) if " " in raw[:19] else raw)
            return dt.date().isoformat()
        except ValueError:
            pass
        if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
            return raw[:10]
        return None

    @staticmethod
    def build_meta_metadata_block(version: str = "OEMetadata-2.0.4") -> dict[str, Any]:
        """Return the ``metaMetadata`` section for OEMetadata 2.0.

        Parameters
        ----------
        version : str, optional
            OEMetadata specification version string.
            Default is ``"OEMetadata-2.0.4"``.

        Returns
        -------
        dict[str, Any]
            ``metaMetadata`` object with ``metadataVersion`` and
            ``metadataLicense``.
        """
        return {
            "metadataVersion": version,
            "metadataLicense": {
                "name": "CC0-1.0",
                "title": "Creative Commons Zero v1.0 Universal",
                "path": "https://creativecommons.org/publicdomain/zero/1.0",
            },
        }

    @staticmethod
    def build_empty_schema_placeholder() -> dict[str, Any]:
        """Minimal ``schema`` when column definitions are not available from the source API.

        Returns
        -------
        dict[str, Any]
            Empty ``fields`` list with an empty ``primaryKey``.
        """
        return {"fields": [], "primaryKey": []}

    def build_oep_resource_path(self, topic: str, table_name: str) -> str:
        """Build the OEP dataedit URL for a table (``path`` field; often read-only on OEP).

        Parameters
        ----------
        topic : str
            OEP topic segment (sanitized before use).
        table_name : str
            OEP table identifier.

        Returns
        -------
        str
            Full ``openenergyplatform.org/dataedit/view/...`` URL.
        """
        topic_seg = sanitize_oep_identifier(topic, fallback="wind")
        return f"{self.OEP_BASE_URL}/dataedit/view/{topic_seg}/{table_name}"

    def build_wedowind_context(self, oep: OepDefaults) -> OemetadataContext:
        """Build the standard WeDoWind context block.

        Parameters
        ----------
        oep : OepDefaults
            OEP publishing defaults containing the publisher name.

        Returns
        -------
        OemetadataContext
            Context object with WeDoWind defaults and configured publisher.
        """
        return OemetadataContext(publisher=oep.publisher)

    def build_resource(
        self,
        *,
        table_name: str,
        title: str,
        description: str,
        file_url: str,
        file_format: str,
        oep: OepDefaults,
        publication_date: str | None,
        licenses: list[OemetadataLicense],
        keywords: list[str],
        sources: list[OemetadataSource] | None = None,
        contributors: list[OemetadataContributor] | None = None,
        schema: dict[str, Any] | None = None,
        dialect: dict[str, str] | OemetadataDialect | None = None,
    ) -> OemetadataResource:
        """Build one OEMetadata resource object for an OEP table.

        Parameters
        ----------
        table_name : str
            OEP table identifier (``name`` field).
        title : str
            Human-readable resource title.
        description : str
            Resource description text.
        file_url : str
            Upstream file URL; appended as an ``OemetadataSource`` when
            non-empty.
        file_format : str
            File format label (e.g. ``"csv"``).
        oep : OepDefaults
            OEP publishing defaults (topic, languages, subject, etc.).
        publication_date : str or None
            ISO ``YYYY-MM-DD`` publication date.
        licenses : list[OemetadataLicense]
            OEMetadata license entries.
        keywords : list[str]
            Resource keyword tags.
        sources : list[OemetadataSource] or None, optional
            Additional provenance sources. Default is ``None``.
        contributors : list[OemetadataContributor] or None, optional
            Pre-built contributor entries. Default is ``None``.
        schema : dict[str, Any] or None, optional
            OEMetadata schema; uses ``build_empty_schema_placeholder`` when
            omitted. Default is ``None``.
        dialect : dict[str, str], OemetadataDialect, or None, optional
            CSV dialect settings. Default is ``OemetadataDialect()``.

        Returns
        -------
        OemetadataResource
            Fully populated resource object ready for serialization.
        """
        topic = oep.topic[0]
        resource_sources = list(sources or [])
        if file_url:
            resource_sources.append(
                OemetadataSource(
                    title=title or table_name,
                    path=file_url,
                    description=description or None,
                    publication_year=(publication_date or "")[:4] or None,
                    source_licenses=licenses or None,
                )
            )
        if isinstance(dialect, dict):
            dialect_obj = OemetadataDialect.from_dict(dialect)
        elif isinstance(dialect, OemetadataDialect):
            dialect_obj = dialect
        else:
            dialect_obj = OemetadataDialect()

        return OemetadataResource(
            name=table_name,
            title=title or table_name,
            path=self.build_oep_resource_path(topic, table_name),
            description=description or "ToDo",
            topics=list(oep.topic),
            languages=list(oep.languages),
            subject=[dict(oep.subject)],
            keywords=keywords,
            publication_date=publication_date,
            context=self.build_wedowind_context(oep),
            licenses=licenses,
            schema=schema if schema else self.build_empty_schema_placeholder(),
            dialect=dialect_obj,
            format=(file_format or "txt").upper()[:32],
            sources=resource_sources,
            contributors=contributors,
        )

    def build_dataset_document(
        self,
        *,
        dataset_name: str,
        title: str,
        description: str,
        resources: list[OemetadataResource | dict[str, Any]],
        oep: OepDefaults,
        dataset_id_uri: str | None = None,
    ) -> dict[str, Any]:
        """Assemble a full OEMetadata document.

        Parameters
        ----------
        dataset_name : str
            Dataset identifier (``name`` field).
        title : str
            Human-readable dataset title.
        description : str
            Dataset description text.
        resources : list[OemetadataResource or dict[str, Any]]
            Resource objects or pre-serialized resource dicts.
        oep : OepDefaults
            OEP publishing defaults (metadata version, etc.).
        dataset_id_uri : str or None, optional
            Optional ``@id`` URI for the dataset. Default is ``None``.

        Returns
        -------
        dict[str, Any]
            Complete OEMetadata 2.0 document.
        """
        resource_dicts = [
            resource.to_dict() if isinstance(resource, OemetadataResource) else resource
            for resource in resources
        ]
        doc: dict[str, Any] = {
            "@context": DEFAULT_OEP_CONTEXT,
            "name": dataset_name,
            "title": title or dataset_name,
            "description": description or "ToDo",
            "resources": resource_dicts,
            "metaMetadata": self.build_meta_metadata_block(oep.metadata_version),
        }
        if dataset_id_uri:
            doc["@id"] = dataset_id_uri
        return doc

    def build_table_name_for_parts(
        self,
        oep: OepDefaults,
        *,
        source_key: str,
        dataset_key: str,
        resource_key: str,
    ) -> str:
        """Derive OEP table name from config prefix and source keys.

        Parameters
        ----------
        oep : OepDefaults
            OEP publishing defaults containing ``table_prefix``.
        source_key : str
            Identifier for the upstream data source.
        dataset_key : str
            Identifier for the dataset within the source.
        resource_key : str
            Identifier for the resource within the dataset.

        Returns
        -------
        str
            Deterministic, sanitized OEP table name.
        """
        return OepTable.build_oep_table_name(
            prefix=oep.table_prefix,
            source_key=source_key,
            dataset_key=dataset_key,
            resource_key=resource_key,
        )
