"""CKAN package_show → OEMetadata for Open Energy Platform (via OMI)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from ckanapi import RemoteCKAN

from mappers.ckan.contributors import contributors_from_package
from mappers.ckan.helpers import (
    ckan_resource_file_format,
    scalar_ckan_text,
)
from mappers.ckan.licenses import build_oemetadata_licenses_from_package
from mappers.oep.oep_defaults import OepDefaults
from mappers.oep.sanitize import cut_oep_identifier, sanitize_oep_identifier
from mappers.oep.oemetadata_builder import OemetadataBuilder
from mappers.oep.oemetadata import OemetadataContributor, OemetadataLicense, OemetadataResource
from mappers.oep.oep_table import OepTable
from mappers.oep.schema_inference import SchemaInference, SchemaInferenceError


@dataclass
class _CkanDatasetContext:
    """Dataset-level fields shared across CKAN resource mappings.

    Attributes
    ----------
    title : str
        Normalized package title.
    description : str
        Normalized package notes/description.
    publication_date : str or None
        ISO publication date from metadata timestamps.
    licenses : list[OemetadataLicense]
        OEMetadata license entries for the package.
    contributors : list[OemetadataContributor]
        OEMetadata contributor entries for the package.
    keywords : list of str
        Provenance, CKAN, and tag keywords.
    package_name : str
        CKAN package name slug.
    package_url : str or None
        Public package URL when available.
    """

    title: str
    description: str
    publication_date: str | None
    licenses: list[OemetadataLicense]
    contributors: list[OemetadataContributor]
    keywords: list[str]
    package_name: str
    package_url: str | None


class CKANToOepMapper:
    """Map CKAN datasets to OEMetadata for the OEP table metadata API.

    Attributes
    ----------
    ckan : RemoteCKAN
        CKAN API client for ``package_show`` and search actions.
    source_key : str
        Source identifier used in table names and keywords.
    builder : OemetadataBuilder
        Helper for assembling OEMetadata documents.
    schema_inference : SchemaInference
        Tabular schema inference from resource URLs.
    _file_session : requests.Session
        HTTP session used for schema inference downloads.
    _last_package : dict or None
        Most recently fetched ``package_show`` result.
    """

    def __init__(
        self,
        ckan_url: str,
        apikey: str | None = None,
        *,
        source_key: str = "ckan",
        builder: OemetadataBuilder | None = None,
        schema_inference: SchemaInference | None = None,
    ):
        """Configure CKAN API access and OEMetadata mapping helpers.

        Parameters
        ----------
        ckan_url : str
            Base URL of the CKAN instance.
        apikey : str or None, optional
            CKAN API key for authenticated requests.
        source_key : str, optional
            Source label for table naming and provenance (default: ``"ckan"``).
        builder : OemetadataBuilder or None, optional
            Custom OEMetadata builder; a new instance is created when omitted.
        schema_inference : SchemaInference or None, optional
            Custom schema inference helper; a new instance is created when omitted.
        """
        self.ckan = RemoteCKAN(ckan_url, apikey=apikey)
        self._file_session = requests.Session()
        self.source_key = source_key
        self._last_package: dict[str, Any] | None = None
        self.builder = builder or OemetadataBuilder()
        self.schema_inference = schema_inference or SchemaInference()

    def map_to_oemetadata(self, dataset_id: str, oep: OepDefaults) -> dict[str, Any]:
        """Map one CKAN package to a full OEMetadata document.

        Parameters
        ----------
        dataset_id : str
            CKAN package id or name accepted by ``package_show``.
        oep : OepDefaults
            OEP publishing defaults (prefix, schema inference, etc.).

        Returns
        -------
        dict
            Complete OEMetadata document for the package.

        Raises
        ------
        RuntimeError
            If the package has no resources with URLs.
        """
        dataset = self._fetch_package(dataset_id)
        context = self._build_dataset_context(dataset, dataset_id, oep)
        resources = self._build_resources(self._mappable_resources(dataset, dataset_id), context, oep)

        return self.builder.build_dataset_document(
            dataset_name=self._build_sanitized_dataset_name(context.package_name, oep),
            title=context.title or context.package_name,
            description=context.description,
            resources=resources,
            oep=oep,
            dataset_id_uri=context.package_url,
        )

    def _fetch_package(self, dataset_id: str) -> dict[str, Any]:
        """Call ``package_show`` and cache the last package dict.

        Parameters
        ----------
        dataset_id : str
            CKAN package id or name.

        Returns
        -------
        dict
            ``package_show`` result; also stored on :attr:`_last_package`.
        """
        print(f"[ckan:oep] package_show id={dataset_id!r} …", flush=True)
        dataset = self.ckan.action.package_show(id=dataset_id)
        if isinstance(dataset, dict):
            self._last_package = dataset
        return dataset

    def _mappable_resources(self, dataset: dict[str, Any], dataset_id: str) -> list[dict[str, Any]]:
        """Return CKAN resources that have a download URL.

        Parameters
        ----------
        dataset : dict
            ``package_show`` result.
        dataset_id : str
            Package id used in error messages.

        Returns
        -------
        list of dict
            Resource dicts with non-empty ``url`` fields.

        Raises
        ------
        RuntimeError
            If no resources have URLs.
        """
        resources_list = [
            res
            for res in dataset.get("resources", [])
            if isinstance(res, dict) and res.get("url")
        ]
        if not resources_list:
            raise RuntimeError(f"CKAN package {dataset_id!r} has no resources with URLs.")
        return resources_list

    def _build_dataset_context(
        self,
        dataset: dict[str, Any],
        dataset_id: str,
        oep: OepDefaults,
    ) -> _CkanDatasetContext:
        """Extract shared dataset metadata from a CKAN package.

        Parameters
        ----------
        dataset : dict
            ``package_show`` result.
        dataset_id : str
            Fallback id when ``dataset["name"]`` is absent.
        oep : OepDefaults
            OEP defaults for provenance keywords.

        Returns
        -------
        _CkanDatasetContext
            Normalized dataset-level fields for resource mapping.
        """
        package_name = str(dataset.get("name") or dataset_id)
        tag_names = [
            str(t["name"]).strip()
            for t in (dataset.get("tags") or [])
            if isinstance(t, dict) and t.get("name")
        ]
        pkg_url = dataset.get("url")
        return _CkanDatasetContext(
            title=self.builder.normalize_plain_text(scalar_ckan_text(dataset.get("title"))),
            description=self.builder.normalize_plain_text(scalar_ckan_text(dataset.get("notes"))),
            publication_date=self.builder.to_publication_date(
                str(dataset.get("metadata_created") or dataset.get("metadata_modified") or "")
            ),
            licenses=build_oemetadata_licenses_from_package(dataset),
            contributors=contributors_from_package(dataset),
            keywords=list(
                dict.fromkeys([oep.provenance_label, "ckan", f"ckan:{package_name}", *tag_names])
            ),
            package_name=package_name,
            package_url=str(pkg_url) if pkg_url else None,
        )

    def _build_resources(
        self,
        resources_list: list[dict[str, Any]],
        context: _CkanDatasetContext,
        oep: OepDefaults,
    ) -> list[OemetadataResource]:
        """Build one OEMetadata resource per CKAN package resource.

        Parameters
        ----------
        resources_list : list of dict
            Mappable CKAN resource dicts.
        context : _CkanDatasetContext
            Shared dataset metadata.
        oep : OepDefaults
            OEP publishing defaults.

        Returns
        -------
        list of OemetadataResource
            One OEMetadata resource per CKAN resource.
        """
        return [
            self._build_resource_from_ckan_resource(res, idx, context, oep)
            for idx, res in enumerate(resources_list)
        ]

    def _build_resource_from_ckan_resource(
        self,
        res: dict[str, Any],
        idx: int,
        context: _CkanDatasetContext,
        oep: OepDefaults,
    ) -> OemetadataResource:
        """Map one CKAN resource dict to an ``OemetadataResource``.

        Parameters
        ----------
        res : dict
            Single CKAN resource from ``package_show``.
        idx : int
            Zero-based resource index within the package.
        context : _CkanDatasetContext
            Shared dataset metadata.
        oep : OepDefaults
            OEP publishing defaults.

        Returns
        -------
        OemetadataResource
            Built OEMetadata resource for the CKAN file.
        """
        url = str(res["url"])
        label = str(res.get("name") or res.get("id") or idx)
        resource_slug = sanitize_oep_identifier(label, fallback=f"res_{idx}")
        fmt = ckan_resource_file_format(res)
        schema, dialect = self._infer_resource_schema(url, fmt, label, oep)

        return self.builder.build_resource(
            table_name=self.builder.table_name_for_parts(
                oep,
                source_key=self.source_key,
                dataset_key=context.package_name,
                resource_key=resource_slug,
            ),
            title=label,
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
        """Infer schema from a resource URL or return a placeholder on failure.

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
                self._file_session,
                url,
                file_format,
                max_lines=oep.schema_sample_lines,
                label=label,
            )
        except SchemaInferenceError as err:
            print(
                f"[ckan:oep] schema infer failed for {label!r}: {err}; "
                "using placeholder schema",
                flush=True,
            )
            return OepTable.minimal_placeholder_schema(), None

    def _build_sanitized_dataset_name(self, package_name: str, oep: OepDefaults) -> str:
        """Build a sanitized OEMetadata dataset ``name`` for the package.

        Parameters
        ----------
        package_name : str
            CKAN package name slug.
        oep : OepDefaults
            OEP defaults providing the table name prefix.

        Returns
        -------
        str
            Truncated, sanitized OEMetadata dataset identifier.
        """
        return cut_oep_identifier(
            sanitize_oep_identifier(
                f"{oep.table_prefix}{self.source_key}_{package_name}",
                fallback="dataset",
            )
        )
