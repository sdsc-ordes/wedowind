"""Zenodo API → OEMetadata for Open Energy Platform (via OMI)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from mappers.oep.oemetadata import OemetadataContributor, OemetadataLicense, OemetadataResource
from mappers.oep.oemetadata_builder import OemetadataBuilder
from mappers.oep.oep_defaults import OepDefaults
from mappers.oep.oep_table import OepTable
from mappers.oep.sanitize import cut_oep_identifier, sanitize_oep_identifier, sanitize_oep_keywords
from mappers.oep.schema_inference import SchemaInference, SchemaInferenceError
from mappers.zenodo.client import ZenodoClient
from mappers.zenodo.contributors import contributors_from_metadata
from mappers.zenodo.licenses import build_oemetadata_licenses_from_metadata
from mappers.zenodo.manage_sources import ZenodoMapperError

_log = logging.getLogger(__name__)


@dataclass
class _ZenodoDatasetContext:
    """Dataset-level fields shared across Zenodo file mappings.

    Attributes
    ----------
    title : str
        Normalized dataset title.
    description : str
        Normalized dataset description.
    publication_date : str or None
        ISO publication date when available.
    licenses : list[OemetadataLicense]
        OEMetadata license entries for the dataset.
    contributors : list[OemetadataContributor]
        OEMetadata contributor entries for the dataset.
    keywords : list of str
        Provenance and Zenodo keyword tags.
    dataset_slug : str
        Sanitized identifier slug for the Zenodo record.
    dataset_uri : str or None
        DOI URI when the record has a DOI.
    """

    title: str
    description: str
    publication_date: str | None
    licenses: list[OemetadataLicense]
    contributors: list[OemetadataContributor]
    keywords: list[str]
    dataset_slug: str
    dataset_uri: str | None


class ZenodoToOepMapper:
    """Map Zenodo records to OEMetadata for the OEP table metadata API.

    Attributes
    ----------
    client : ZenodoClient
        HTTP client for Zenodo record and file access.
    source_key : str
        Source identifier used in table names and keywords.
    builder : OemetadataBuilder
        Helper for assembling OEMetadata documents.
    schema_inference : SchemaInference
        Optional tabular schema inference from file URLs.
    """

    def __init__(
        self,
        zenodo_base_url: str = "https://zenodo.org",
        access_token: str | None = None,
        *,
        source_key: str = "zenodo",
        builder: OemetadataBuilder | None = None,
        schema_inference: SchemaInference | None = None,
    ):
        """Configure Zenodo API access and OEMetadata mapping helpers.

        Parameters
        ----------
        zenodo_base_url : str, optional
            Base URL of the Zenodo instance (default: ``https://zenodo.org``).
        access_token : str or None, optional
            Bearer token for authenticated API calls; falls back to
            ``ZENODO_ACCESS_TOKEN`` when omitted.
        source_key : str, optional
            Source label for table naming and provenance (default: ``"zenodo"``).
        builder : OemetadataBuilder or None, optional
            Custom OEMetadata builder; a new instance is created when omitted.
        schema_inference : SchemaInference or None, optional
            Custom schema inference helper; a new instance is created when omitted.
        """
        self.client = ZenodoClient(zenodo_base_url=zenodo_base_url, access_token=access_token)
        self.source_key = source_key
        self.builder = builder or OemetadataBuilder()
        self.schema_inference = schema_inference or SchemaInference()

    def map_to_oemetadata(self, dataset_id: str, oep: OepDefaults) -> dict[str, Any]:
        """Map one Zenodo record to a full OEMetadata document.

        Parameters
        ----------
        dataset_id : str
            Zenodo record id or DOI slug.
        oep : OepDefaults
            OEP publishing defaults (prefix, schema inference, etc.).

        Returns
        -------
        dict
            Complete OEMetadata document for the record.

        Raises
        ------
        ZenodoMapperError
            If the record has no files or no mappable file URLs.
        """
        record, metadata = self._load_record(dataset_id)
        files = self._get_mappable_files(record, dataset_id)
        context = self._build_dataset_context(record, metadata, dataset_id, oep)
        resources = self._build_resources(files, context, oep)
        if not resources:
            raise ZenodoMapperError(f"Zenodo record {dataset_id!r}: no mappable file URLs.")

        return self.builder.build_dataset_document(
            dataset_name=self._build_sanitized_dataset_name(context.dataset_slug, oep),
            title=context.title,
            description=context.description,
            resources=resources,
            oep=oep,
            dataset_id_uri=context.dataset_uri,
        )

    def _load_record(self, dataset_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """Fetch a Zenodo record and return ``(record, metadata)``.

        Parameters
        ----------
        dataset_id : str
            Zenodo record id or DOI slug.

        Returns
        -------
        tuple of (dict, dict)
            Full API record payload and its ``metadata`` sub-object (may be empty).

        Raises
        ------
        ZenodoMapperError
            Propagated from :meth:`ZenodoClient.get_record`.
        """
        record = self.client.get_record(dataset_id)
        metadata = record.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        return record, metadata

    def _get_mappable_files(self, record: dict[str, Any], dataset_id: str) -> list[Any]:
        """Return the record file list or raise when empty.

        Parameters
        ----------
        record : dict
            Zenodo API record payload.
        dataset_id : str
            Record id used in error messages.

        Returns
        -------
        list
            Non-empty ``files`` list from the record.

        Raises
        ------
        ZenodoMapperError
            If ``files`` is missing, not a list, or empty.
        """
        files = record.get("files", [])
        if not isinstance(files, list) or not files:
            raise ZenodoMapperError(f"Zenodo record {dataset_id!r} has no files to map.")
        return files

    def _build_dataset_context(
        self,
        record: dict[str, Any],
        metadata: dict[str, Any],
        dataset_id: str,
        oep: OepDefaults,
    ) -> _ZenodoDatasetContext:
        """Extract shared dataset metadata from a Zenodo record.

        Parameters
        ----------
        record : dict
            Full Zenodo API record payload.
        metadata : dict
            Record ``metadata`` sub-object.
        dataset_id : str
            Fallback id when ``record["id"]`` is absent.
        oep : OepDefaults
            OEP defaults for provenance keywords.

        Returns
        -------
        _ZenodoDatasetContext
            Normalized dataset-level fields for resource mapping.
        """
        title = self.builder.normalize_plain_text(
            str(metadata.get("title") or record.get("title") or f"zenodo-{dataset_id}")
        )
        description = self.builder.normalize_plain_text(str(metadata.get("description") or ""))
        pub_date = self.builder.parse_publication_date(
            str(metadata.get("publication_date") or record.get("created") or "")
        )
        doi = metadata.get("doi")
        dataset_uri = f"https://doi.org/{doi}" if isinstance(doi, str) and doi.strip() else None
        return _ZenodoDatasetContext(
            title=title,
            description=description,
            publication_date=pub_date,
            licenses=build_oemetadata_licenses_from_metadata(metadata),
            contributors=contributors_from_metadata(metadata),
            keywords=sanitize_oep_keywords(
                [
                    oep.provenance_label,
                    "zenodo",
                    f"zenodo:{dataset_id}",
                    *(str(k) for k in (metadata.get("keywords") or []) if k),
                ]
            ),
            dataset_slug=sanitize_oep_identifier(
                str(record.get("id") or dataset_id), fallback="ds"
            ),
            dataset_uri=dataset_uri,
        )

    def _build_resources(
        self,
        files: list[Any],
        context: _ZenodoDatasetContext,
        oep: OepDefaults,
    ) -> list[OemetadataResource]:
        """Build one OEMetadata resource per Zenodo file with a URL.

        Parameters
        ----------
        files : list
            Zenodo ``files`` entries from the record payload.
        context : _ZenodoDatasetContext
            Shared dataset metadata for each resource.
        oep : OepDefaults
            OEP publishing defaults.

        Returns
        -------
        list of OemetadataResource
            Mappable resources; entries without URLs are skipped.
        """
        resources: list[OemetadataResource] = []
        for idx, file_info in enumerate(files):
            resource = self._build_resource_from_file(file_info, idx, context, oep)
            if resource is not None:
                resources.append(resource)
        return resources

    def _build_resource_from_file(
        self,
        file_info: Any,
        idx: int,
        context: _ZenodoDatasetContext,
        oep: OepDefaults,
    ) -> OemetadataResource | None:
        """Map one Zenodo file entry to an ``OemetadataResource``, or skip when unmappable.

        Parameters
        ----------
        file_info : Any
            Single element from the record ``files`` list.
        idx : int
            Zero-based file index within the record.
        context : _ZenodoDatasetContext
            Shared dataset metadata.
        oep : OepDefaults
            OEP publishing defaults.

        Returns
        -------
        OemetadataResource or None
            Built resource, or ``None`` when the entry is not a dict or has no URL.
        """
        if not isinstance(file_info, dict):
            return None
        url = ZenodoClient.file_url(file_info)
        if not url:
            return None

        file_key = str(file_info.get("key") or file_info.get("filename") or idx)
        resource_slug = re.sub(r"\.[^.]+$", "", file_key) or f"file_{idx}"
        fmt = ZenodoClient.infer_file_format(file_info)
        schema, dialect = self._infer_resource_schema(url, fmt, file_key, oep)

        return self.builder.build_resource(
            table_name=self.builder.build_table_name_for_parts(
                oep,
                source_key=self.source_key,
                dataset_key=context.dataset_slug,
                resource_key=resource_slug,
            ),
            title=file_key,
            description=context.description or context.title,
            file_url=url,
            file_format=fmt,
            oep=oep,
            publication_date=context.publication_date,
            licenses=context.licenses,
            keywords=context.keywords,
            contributors=context.contributors if idx == 0 else None,
            schema=schema,
            dialect=dialect,
        )

    def _infer_resource_schema(
        self,
        url: str,
        file_format: str,
        label: str,
        oep: OepDefaults,
    ) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
        """Infer schema from a file URL or return a placeholder on failure.

        Parameters
        ----------
        url : str
            Download URL for the tabular file.
        file_format : str
            Lowercase format token (e.g. ``csv``).
        label : str
            Human-readable label for log messages.
        oep : OepDefaults
            OEP defaults controlling schema inference.

        Returns
        -------
        tuple of (dict or None, dict or None)
            Inferred Frictionless schema and dialect, ``(None, None)`` when
            inference is disabled, or a placeholder schema on inference failure.
        """
        if not oep.infer_schema or not self.schema_inference.is_tabular_file_format(file_format):
            return None, None
        try:
            return self.schema_inference.infer_from_source_url(
                self.client.session,
                url,
                file_format,
                max_lines=oep.schema_sample_lines,
                label=label,
            )
        except SchemaInferenceError as err:
            _log.warning(
                "schema inference failed for %r (url=%s): %s — publishing with placeholder schema (id column only)",
                label, url, err,
            )
            return OepTable.build_minimal_placeholder_schema(), None

    def _build_sanitized_dataset_name(self, dataset_slug: str, oep: OepDefaults) -> str:
        """Build a sanitized OEMetadata dataset ``name`` for the record.

        Parameters
        ----------
        dataset_slug : str
            Sanitized Zenodo record slug.
        oep : OepDefaults
            OEP defaults providing the table name prefix.

        Returns
        -------
        str
            Truncated, sanitized OEMetadata dataset identifier.
        """
        return cut_oep_identifier(
            sanitize_oep_identifier(
                f"{oep.table_prefix}{self.source_key}_{dataset_slug}",
                fallback="dataset",
            )
        )
