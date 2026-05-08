"""Zenodo API → Databus dataset payloads (files may be streamed for SHA-256)."""

from __future__ import annotations

import os
import re
from typing import Any

import databusclient
import requests

from databus_local_manager.load_env import load_dotenv_if_available
from mappers.compute_sha256 import (
    declared_sha256_tuple_if_present,
    sha256_tuple_for_distribution_url,
)
from mappers.licenses import normalize_zenodo_license_for_databus
from mappers.utils import (
    GroupMetadata,
    get_databus_identifier,
    sanitize_dataset_text_fields,
)
from mappers.zenodo.manage_sources import (
    DEFAULT_SOURCES_PATH as DEFAULT_SOURCES_PATH,
    DEFAULT_TIMESTAMP_PATH as DEFAULT_TIMESTAMP_PATH,
    DEFAULT_TIMESTAMP_STATE as DEFAULT_TIMESTAMP_STATE,
    SOURCE_QUERY_PARAMS,
    ZenodoMapperError,
    load_source_config as load_source_config,
    load_source_query_params as load_source_query_params,
    load_timestamp_state as load_timestamp_state,
    save_timestamp_state as save_timestamp_state,
)

DEFAULT_ZENODO_BASE_URL = "https://zenodo.org"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_AUTH_MAX_PAGE_SIZE = 100
DEFAULT_ANON_MAX_PAGE_SIZE = 25


class ZenodoToDataBusMapper:
    """Map Zenodo ``/api/records`` resources to Databus dataset JSON-LD via databusclient.

    Attributes
    ----------
    zenodo_base_url : str
        Base URL for the Zenodo instance (no trailing slash).
    access_token : str or None
        Optional bearer token; enables higher page-size limits when set.
    session : requests.Session
        HTTP session for JSON GETs (``Accept: application/json``; ``Authorization`` when token set).

    Methods
    -------
    __init__(zenodo_base_url, access_token)
        Configure API endpoint and optional authentication.
    map_to_databus_dataset(dataset_id, group)
        Fetch ``GET /api/records/{id}`` and build a databusclient dataset dict.
    fetch_source_records(source_key, page, size)
        Query ``GET /api/records`` for a configured incremental source.
    _get_record(dataset_id)
        Fetch single-record JSON (Zenodo terminology).
    _request_json(path, params)
        Perform authenticated GET and parse JSON (raises on HTTP/API errors).
    _sha256_tuple_for_zenodo_file(file_info, idx)
        Resolve SHA-256 and byte length for one file entry.
    _build_distributions(files)
        Build databusclient distribution list from Zenodo ``files`` array.
    _extract_title(zenodo_record, metadata)
        Derive plain title string.
    _extract_abstract(metadata)
        Abstract from metadata description.
    _extract_description(metadata)
        Long description (same source as abstract for Zenodo).
    _extract_version(zenodo_record, metadata)
        Version segment for the Databus identifier.
    _artifact_name(zenodo_record, metadata)
        Slug for the artifact path segment.
    _file_url(file_info)
        Resolve a download URL for a file dict.
    _infer_file_format(file_info)
        File extension for Databus ``file_format``.
    _normalize_text(value)
        Strip HTML-like tags and collapse whitespace.
    """

    def __init__(
        self,
        zenodo_base_url: str = DEFAULT_ZENODO_BASE_URL,
        access_token: str | None = None,
    ):
        """Configure Zenodo API base URL and optional OAuth token.

        Parameters
        ----------
        zenodo_base_url : str, optional
            Zenodo root URL (default ``https://zenodo.org``).
        access_token : str or None, optional
            Bearer token; defaults to :envvar:`ZENODO_ACCESS_TOKEN` when omitted.

        Returns
        -------
        None
        """
        load_dotenv_if_available()
        self.zenodo_base_url = zenodo_base_url.rstrip("/")
        self.access_token = access_token or os.getenv("ZENODO_ACCESS_TOKEN")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if self.access_token:
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

    def map_to_databus_dataset(self, dataset_id: str, group: GroupMetadata) -> dict[str, Any]:
        """Build a databusclient dataset dict for one Zenodo numeric id.

        Parameters
        ----------
        dataset_id : str
            Zenodo dataset id (same id used in ``GET /api/records/{id}``).
        group : GroupMetadata
            Databus group metadata for JSON-LD.

        Returns
        -------
        dict[str, Any]
            Payload suitable for :func:`mappers.databus.post_register_payload`.

        Raises
        ------
        ZenodoMapperError
            From :meth:`_get_record`, :meth:`_build_distributions`, or checksum helpers when
            mapping cannot complete.
        """
        zenodo_record = self._get_record(dataset_id)
        metadata = zenodo_record.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        distributions = self._build_distributions(zenodo_record.get("files", []))
        title, abstract, description = sanitize_dataset_text_fields(
            self._extract_title(zenodo_record, metadata),
            self._extract_abstract(metadata),
            self._extract_description(metadata),
        )
        artifact_name = self._artifact_name(zenodo_record, metadata)
        version = self._extract_version(zenodo_record, metadata)
        version_id = get_databus_identifier(group.name, artifact_name, version)
        license_url = normalize_zenodo_license_for_databus(metadata)

        return databusclient.create_dataset(
            version_id,
            title=title,
            abstract=abstract,
            description=description,
            license_url=license_url,
            distributions=distributions,
            group_title=group.title,
            group_abstract=group.abstract,
            group_description=group.description,
        )

    def fetch_source_records(
        self, source_key: str, page: int = 1, size: int = 100
    ) -> list[dict[str, Any]]:
        """Return hit rows from ``GET /api/records`` for a configured source key.

        Parameters
        ----------
        source_key : str
            Key present in ``sources.json`` / :data:`SOURCE_QUERY_PARAMS`.
        page : int, optional
            Result page (default ``1``).
        size : int, optional
            Page size; capped by auth/anonymous Zenodo limits (default ``100``).

        Returns
        -------
        list[dict[str, Any]]
            Zenodo hit dicts (typically include ``id``, ``updated``, metadata).

        Raises
        ------
        ValueError
            If ``source_key`` is unknown.
        ZenodoMapperError
            On unexpected response shape or HTTP errors from :meth:`_request_json`.
        """
        if source_key not in SOURCE_QUERY_PARAMS:
            raise ValueError(f"Unknown source key: {source_key}")

        page_size_limit = (
            DEFAULT_AUTH_MAX_PAGE_SIZE if self.access_token else DEFAULT_ANON_MAX_PAGE_SIZE
        )
        normalized_size = max(1, min(int(size), page_size_limit))
        params = {
            **SOURCE_QUERY_PARAMS[source_key],
            "sort": "-mostrecent",
            "all_versions": "true",
            "page": page,
            "size": normalized_size,
        }
        payload = self._request_json("/api/records", params=params)
        hits = payload.get("hits", {}).get("hits")
        if isinstance(hits, list):
            return [row for row in hits if isinstance(row, dict)]
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        raise ZenodoMapperError("Unexpected records list response format.")

    def _get_record(self, dataset_id: str) -> dict[str, Any]:
        """Fetch ``GET /api/records/{id}`` JSON (Zenodo calls this a record).

        Parameters
        ----------
        dataset_id : str
            Numeric Zenodo id.

        Returns
        -------
        dict[str, Any]
            Parsed record body.

        Raises
        ------
        ZenodoMapperError
            On non-dict JSON or HTTP errors from :meth:`_request_json`.
        """
        payload = self._request_json(f"/api/records/{dataset_id}")
        if not isinstance(payload, dict):
            raise ZenodoMapperError(f"Zenodo API record {dataset_id!r} returned invalid payload.")
        return payload

    def _request_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """HTTP GET JSON from Zenodo.

        Parameters
        ----------
        path : str
            Path relative to :attr:`zenodo_base_url` (e.g. ``/api/records``).
        params : dict or None, optional
            Query parameters.

        Returns
        -------
        Any
            Parsed JSON (typically ``dict`` or ``list``).

        Raises
        ------
        ZenodoMapperError
            On 401/403/404 or other HTTP errors after :meth:`requests.Response.raise_for_status`.
        """
        url = f"{self.zenodo_base_url}{path}"
        print(
            f"[zenodo:api] HTTP GET {url} (timeout {DEFAULT_TIMEOUT_SECONDS}s) …",
            flush=True,
        )
        if params:
            preview = {k: str(v)[:120] for k, v in params.items()}
            print(f"[zenodo:api]   query: {preview}", flush=True)
        response = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT_SECONDS)
        if response.status_code in (401, 403):
            raise ZenodoMapperError(f"Zenodo API unauthorized for {url} ({response.status_code}).")
        if response.status_code == 404:
            raise ZenodoMapperError(f"Zenodo resource not found: {url}")
        try:
            response.raise_for_status()
        except requests.HTTPError as err:
            details = ""
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    message = payload.get("message")
                    if message:
                        details = f": {message}"
            except ValueError:
                pass
            raise ZenodoMapperError(
                f"Zenodo API error {response.status_code} for {url}{details}"
            ) from err
        print(f"[zenodo:api] OK {response.status_code} for {path}", flush=True)
        return response.json()

    def _sha256_tuple_for_zenodo_file(self, file_info: dict[str, Any], idx: int) -> tuple[str, int]:
        """Return SHA-256 hex and byte length for one Zenodo file entry.

        Uses declared ``sha256:`` checksum when present; otherwise streams the download URL.

        Parameters
        ----------
        file_info : dict[str, Any]
            Zenodo ``files`` element.
        idx : int
            Index for error messages.

        Returns
        -------
        tuple[str, int]
            ``(sha256_hex_lower, size_bytes)``.

        Raises
        ------
        ZenodoMapperError
            If no usable URL exists for streaming when checksum is missing.
        """
        declared = declared_sha256_tuple_if_present(file_info)
        if declared is not None:
            name = str(file_info.get("key") or idx)
            print(
                f"[zenodo:checksum] {name!r}: using Zenodo-declared sha256 (no download)",
                flush=True,
            )
            return declared

        url = self._file_url(file_info)
        if not url:
            raise ZenodoMapperError(f"File entry at index {idx} has no download URL.")
        name = str(file_info.get("key") or idx)
        expected = file_info.get("size") if isinstance(file_info.get("size"), int) else None
        chk = file_info.get("checksum")
        hint = ""
        if isinstance(chk, str) and "md5" in chk.lower():
            hint = " Zenodo only provides MD5; databus needs SHA-256, so the file is streamed once."
        print(
            f"[zenodo:checksum] {name!r}: streaming URL to compute SHA-256 for Databus "
            f"(declared size={expected})…{hint}",
            flush=True,
        )
        return sha256_tuple_for_distribution_url(
            self.session, url, label=name, expected_size=expected, resource=None
        )

    def _build_distributions(self, files: Any) -> list[Any]:
        """Build databusclient distributions for Zenodo ``files`` array.

        Parameters
        ----------
        files : Any
            Zenodo ``files`` list from the record JSON.

        Returns
        -------
        list[Any]
            List of distribution objects from ``databusclient.create_distribution``.

        Raises
        ------
        ZenodoMapperError
            If ``files`` is empty or entries are malformed / missing URLs.
        """
        if not isinstance(files, list) or not files:
            raise ZenodoMapperError("Zenodo API record has no files to map.")

        print(
            "[zenodo:payload] Building distributions: databusclient needs SHA-256 + byte size per file. "
            "If Zenodo does not declare sha256:…, each file is downloaded once (see logs below).",
            flush=True,
        )
        out: list[Any] = []
        multi = len(files) > 1
        for idx, file_info in enumerate(files):
            if not isinstance(file_info, dict):
                raise ZenodoMapperError(f"Unexpected file entry at index {idx}.")
            url = self._file_url(file_info)
            if not url:
                raise ZenodoMapperError(f"File entry at index {idx} has no download URL.")
            sha_tuple = self._sha256_tuple_for_zenodo_file(file_info, idx)
            file_format = self._infer_file_format(file_info)
            cvs = {"type": "zenodo-file"}
            if multi:
                cvs["part"] = str(idx)
            out.append(
                databusclient.create_distribution(
                    url=url,
                    cvs=cvs,
                    file_format=file_format,
                    sha256_length_tuple=sha_tuple,
                )
            )
        return out

    def _extract_title(self, zenodo_record: dict[str, Any], metadata: dict[str, Any]) -> str:
        """Plain title string for the dataset.

        Parameters
        ----------
        zenodo_record : dict[str, Any]
            Full Zenodo record JSON.
        metadata : dict[str, Any]
            ``record['metadata']`` mapping.

        Returns
        -------
        str
            Normalized title text.
        """
        title = (
            metadata.get("title")
            or zenodo_record.get("title")
            or f"zenodo-{zenodo_record.get('id', 'record')}"
        )
        return self._normalize_text(str(title))

    def _extract_abstract(self, metadata: dict[str, Any]) -> str:
        """Abstract text from Zenodo metadata description.

        Parameters
        ----------
        metadata : dict[str, Any]
            Zenodo metadata dict.

        Returns
        -------
        str
            Normalized abstract.
        """
        return self._normalize_text(str(metadata.get("description") or ""))

    def _extract_description(self, metadata: dict[str, Any]) -> str:
        """Long description (same source as abstract for Zenodo).

        Parameters
        ----------
        metadata : dict[str, Any]
            Zenodo metadata dict.

        Returns
        -------
        str
            Normalized description.
        """
        return self._normalize_text(str(metadata.get("description") or ""))

    def _extract_version(self, zenodo_record: dict[str, Any], metadata: dict[str, Any]) -> str:
        """Version segment for the Databus identifier.

        Parameters
        ----------
        zenodo_record : dict[str, Any]
            Full Zenodo record JSON.
        metadata : dict[str, Any]
            Zenodo metadata dict.

        Returns
        -------
        str
            Sanitized version string.
        """
        value = (
            metadata.get("version")
            or zenodo_record.get("updated")
            or zenodo_record.get("created")
            or zenodo_record.get("id")
        )
        return self._normalize_text(str(value))

    def _artifact_name(self, zenodo_record: dict[str, Any], metadata: dict[str, Any]) -> str:
        """Slug for artifact segment of the version URI.

        Parameters
        ----------
        zenodo_record : dict[str, Any]
            Full Zenodo record JSON.
        metadata : dict[str, Any]
            Zenodo metadata dict.

        Returns
        -------
        str
            Lowercase hyphenated slug.
        """
        slug_source = metadata.get("title") or zenodo_record.get("id") or "zenodo-record"
        slug = re.sub(r"[^a-z0-9]+", "-", str(slug_source).lower()).strip("-")
        return slug or f"zenodo-{zenodo_record.get('id', 'record')}"

    def _file_url(self, file_info: dict[str, Any]) -> str:
        """Resolve best download URL for a Zenodo file dict.

        Parameters
        ----------
        file_info : dict[str, Any]
            One element of Zenodo ``files``.

        Returns
        -------
        str
            HTTP URL string, or empty string if none found.
        """
        links = file_info.get("links")
        if isinstance(links, dict):
            for key in ("self", "download", "content"):
                value = links.get(key)
                if value:
                    return str(value)
        for key in ("self", "download"):
            value = file_info.get(key)
            if value:
                return str(value)
        return ""

    def _infer_file_format(self, file_info: dict[str, Any]) -> str:
        """Infer Databus ``file_format`` from filename extension.

        Parameters
        ----------
        file_info : dict[str, Any]
            Zenodo file dict.

        Returns
        -------
        str
            Lowercase extension, or ``txt`` when missing.
        """
        candidate = str(file_info.get("key") or file_info.get("filename") or "")
        if "." not in candidate:
            return "txt"
        return candidate.rsplit(".", maxsplit=1)[-1].lower() or "txt"

    def _normalize_text(self, value: str) -> str:
        """Strip HTML-like tags and collapse whitespace.

        Parameters
        ----------
        value : str
            Raw text.

        Returns
        -------
        str
            Plain text suitable for Databus fields.
        """
        no_html = re.sub(r"<[^>]+>", " ", value)
        return " ".join(no_html.split())
