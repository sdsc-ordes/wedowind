"""Zenodo REST API client for OEP metadata mapping."""

from __future__ import annotations

import os
from typing import Any

import requests

from mappers.load_env import load_dotenv_if_available
from mappers.zenodo.manage_sources import SOURCE_QUERY_PARAMS, ZenodoMapperError

DEFAULT_ZENODO_BASE_URL = "https://zenodo.org"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_AUTH_MAX_PAGE_SIZE = 100
DEFAULT_ANON_MAX_PAGE_SIZE = 25


class ZenodoClient:
    """HTTP access to Zenodo ``/api/records`` for metadata mappers.

    Attributes
    ----------
    zenodo_base_url : str
        Base URL without trailing slash.
    access_token : str or None
        Bearer token when authenticated requests are required.
    session : requests.Session
        Reusable HTTP session with JSON accept headers.
    """

    def __init__(
        self,
        zenodo_base_url: str = DEFAULT_ZENODO_BASE_URL,
        access_token: str | None = None,
    ):
        """Create a configured HTTP session for Zenodo API calls.

        Parameters
        ----------
        zenodo_base_url : str, optional
            Zenodo instance base URL (default: :data:`DEFAULT_ZENODO_BASE_URL`).
        access_token : str or None, optional
            API token; falls back to ``ZENODO_ACCESS_TOKEN`` when omitted.
        """
        load_dotenv_if_available()
        self.zenodo_base_url = zenodo_base_url.rstrip("/")
        self.access_token = access_token or os.getenv("ZENODO_ACCESS_TOKEN")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if self.access_token:
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

    def fetch_source_records(
        self, source_key: str, page: int = 1, size: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch one page of records for a configured source query.

        Parameters
        ----------
        source_key : str
            Key into :data:`SOURCE_QUERY_PARAMS`.
        page : int, optional
            One-based page number (default: 1).
        size : int, optional
            Page size, capped by auth/anonymous limits (default: 100).

        Returns
        -------
        list of dict
            Record dicts from the ``hits.hits`` array.

        Raises
        ------
        ValueError
            If ``source_key`` is not configured.
        ZenodoMapperError
            On HTTP errors or unexpected response shape.
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

    def get_record(self, dataset_id: str) -> dict[str, Any]:
        """Fetch a single Zenodo record by id or DOI.

        Parameters
        ----------
        dataset_id : str
            Numeric record id or DOI slug accepted by ``/api/records/{id}``.

        Returns
        -------
        dict
            Parsed JSON record payload.

        Raises
        ------
        ZenodoMapperError
            On HTTP errors or when the payload is not a dict.
        """
        payload = self._request_json(f"/api/records/{dataset_id}")
        if not isinstance(payload, dict):
            raise ZenodoMapperError(f"Zenodo API record {dataset_id!r} returned invalid payload.")
        return payload

    def _request_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Perform a GET request and return parsed JSON with logging.

        Parameters
        ----------
        path : str
            API path appended to :attr:`zenodo_base_url`.
        params : dict or None, optional
            Query string parameters.

        Returns
        -------
        Any
            Parsed JSON response body.

        Raises
        ------
        ZenodoMapperError
            On 401, 403, 404, or other HTTP errors.
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

    @staticmethod
    def file_url(file_info: dict[str, Any]) -> str:
        """Resolve the best download URL from a Zenodo file object.

        Parameters
        ----------
        file_info : dict
            Single file entry from a Zenodo record ``files`` list.

        Returns
        -------
        str
            Download URL, or an empty string when none is found.
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

    @staticmethod
    def infer_file_format(file_info: dict[str, Any]) -> str:
        """Guess a lowercase format token from the Zenodo file name.

        Parameters
        ----------
        file_info : dict
            Single file entry from a Zenodo record ``files`` list.

        Returns
        -------
        str
            Lowercase extension without dot, or ``"txt"`` when unknown.
        """
        candidate = str(file_info.get("key") or file_info.get("filename") or "")
        if "." not in candidate:
            return "txt"
        return candidate.rsplit(".", maxsplit=1)[-1].lower() or "txt"
