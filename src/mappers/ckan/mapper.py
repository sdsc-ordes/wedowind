"""Map CKAN ``package_show`` datasets to Databus dataset payloads."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import databusclient
import requests
from ckanapi import RemoteCKAN

from mappers.compute_sha256 import sha256_tuple_for_distribution_url
from mappers.licenses import normalize_ckan_license_for_databus
from mappers.utils import (
    GroupMetadata,
    get_databus_identifier,
    sanitize_databus_uri_segment,
    sanitize_dataset_text_fields,
)


def _ckan_resource_cv_type(resource: dict[str, Any]) -> str:
    """CV ``type`` string for Databus content-variant metadata.

    CKAN ``resource_type`` / ``type`` may contain spaces; output is URI-safe.

    Parameters
    ----------
    resource : dict[str, Any]
        CKAN resource dict.

    Returns
    -------
    str
        Sanitized token (default ``data``).
    """
    t = resource.get("resource_type") or resource.get("type")
    if t is None:
        return "data"
    s = str(t).strip().lower()
    if not s or s == "none":
        return "data"
    return sanitize_databus_uri_segment(s, fallback="data")


def _ckan_resource_file_format(resource: dict[str, Any]) -> str:
    """Lowercase format token for Databus; sanitize values such as ``SHP ZIP``.

    Parameters
    ----------
    resource : dict[str, Any]
        CKAN resource dict.

    Returns
    -------
    str
        Sanitized extension-like token (default ``txt``).
    """
    fmt = resource.get("format")
    if fmt is None:
        return "txt"
    s = str(fmt).strip().lower()
    if not s or s == "none":
        return "txt"
    return sanitize_databus_uri_segment(s, fallback="txt")


def _scalar_ckan_text(value: Any) -> str | None:
    """Coerce CKAN text fields that may be strings or lists.

    Parameters
    ----------
    value : Any
        Raw CKAN field value.

    Returns
    -------
    str or None
        Joined string, or ``None`` when empty.
    """
    if value is None:
        return None
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if item is not None]
        joined = ", ".join(p for p in parts if p)
        return joined or None
    return str(value)


def iter_package_search_results(
    ckan: RemoteCKAN, params: dict[str, Any]
) -> Iterator[dict[str, Any]]:
    """Yield all packages from paginated ``package_search``.

    Parameters
    ----------
    ckan : ckanapi.RemoteCKAN
        Connected CKAN client.
    params : dict[str, Any]
        ``package_search`` arguments except ``rows`` / ``start`` (added internally).

    Yields
    ------
    dict[str, Any]
        CKAN package dicts from each page.

    Notes
    -----
    Stops when a batch is shorter than ``rows``, ``start`` reaches ``count``, or the response
    shape is invalid (logs and breaks).
    """
    page_rows = int(params.get("rows") or 100)
    page_rows = max(1, min(page_rows, 1000))
    base = {k: v for k, v in params.items() if k not in {"rows", "start"}}
    start = 0
    page_num = 0
    while True:
        page_num += 1
        fq_preview = str(base.get("fq") or "")[:80]
        print(
            f"[ckan:api] package_search page={page_num} start={start} rows={page_rows} "
            f"fq_prefix={fq_preview!r} …",
            flush=True,
        )
        result = ckan.action.package_search(rows=page_rows, start=start, **base)
        if not isinstance(result, dict):
            print(
                "[ckan:api] package_search: unexpected non-dict response; stopping.",
                flush=True,
            )
            break
        batch = result.get("results") or []
        if not isinstance(batch, list):
            print(
                "[ckan:api] package_search: unexpected results shape; stopping.",
                flush=True,
            )
            break
        total = result.get("count")
        total_s = total if isinstance(total, int) else "?"
        print(
            f"[ckan:api] OK package_search got={len(batch)} total_count={total_s} next_start={start + len(batch)}",
            flush=True,
        )
        for pkg in batch:
            if isinstance(pkg, dict):
                yield pkg
        if len(batch) < page_rows:
            break
        start += len(batch)
        if isinstance(total, int) and start >= total:
            break


class CKANToDataBusMapper:
    """Build Databus dataset payloads from a CKAN catalog via ``RemoteCKAN``.

    Attributes
    ----------
    ckan : ckanapi.RemoteCKAN
        Client used for ``package_show`` / ``package_search``.
    _file_session : requests.Session
        Session for streaming resource URLs when computing SHA-256 for Databus.
    _last_ckan_package : dict[str, Any] or None
        Last package dict returned by :meth:`map_to_databus_dataset`, for checkpoint timestamps.

    Methods
    -------
    __init__(ckan_url, apikey)
        Construct ``RemoteCKAN`` for the given base URL.
    map_to_databus_dataset(dataset_id, group)
        Call ``package_show`` and return a databusclient dataset dict.
    """

    def __init__(self, ckan_url, apikey: str | None = None):
        """Connect to a CKAN instance.

        Parameters
        ----------
        ckan_url : str
            CKAN site base URL.
        apikey : str or None, optional
            Reserved for future authenticated calls (currently unused).

        Returns
        -------
        None
        """
        self.ckan = RemoteCKAN(ckan_url)
        self._file_session = requests.Session()
        self._last_ckan_package: dict[str, Any] | None = None

    def map_to_databus_dataset(self, dataset_id: str, group: GroupMetadata) -> Any:
        """Fetch one dataset by id and build the databusclient registration payload.

        Parameters
        ----------
        dataset_id : str
            CKAN package name or id accepted by ``package_show``.
        group : GroupMetadata
            Databus group metadata.

        Returns
        -------
        Any
            Dataset dict from ``databusclient.create_dataset``.

        Raises
        ------
        Exception
            Propagated from ``ckanapi`` / CKAN API when ``package_show`` fails, or from
            :func:`mappers.compute_sha256.sha256_tuple_for_distribution_url` when a resource
            URL cannot be streamed.

        Notes
        -----
        ``databusclient.create_dataset`` downloads each file if checksum/size are missing from
        distribution strings (no progress, loads whole body into RAM). This mapper therefore
        streams each resource URL once to compute SHA-256 + size (same approach as Zenodo) and
        passes ``sha256_length_tuple`` into ``create_distribution``.

        Sets :attr:`_last_ckan_package` to the raw CKAN package dict on success for callers that
        update checkpoints.
        """
        self._last_ckan_package = None
        print(f"[ckan:api] package_show id={dataset_id!r} …", flush=True)
        dataset = self.ckan.action.package_show(id=dataset_id)
        if isinstance(dataset, dict):
            self._last_ckan_package = dataset
        title_preview = str(dataset.get("title") or "")[:72]
        print(
            f"[ckan:api] OK package_show name={dataset.get('name')!r} "
            f"title_preview={title_preview!r}",
            flush=True,
        )

        resources_list = [
            res for res in dataset.get("resources", []) if isinstance(res, dict) and res.get("url")
        ]
        multi = len(resources_list) > 1
        distributions = []
        n_res = len(resources_list)
        for idx, res in enumerate(resources_list):
            cvs: dict[str, str] = {"type": _ckan_resource_cv_type(res)}
            # Databus requires distinct content variants when format/compression match (many CKAN zips).
            if multi:
                cvs["part"] = str(idx)
            url = str(res["url"])
            label = str(res.get("name") or res.get("id") or idx)
            expected = res.get("size") if isinstance(res.get("size"), int) else None
            print(
                f"[ckan:checksum] resource {idx + 1}/{n_res} in this dataset · SHA-256 for {label!r} …",
                flush=True,
            )
            sha_tuple = sha256_tuple_for_distribution_url(
                self._file_session,
                url,
                label=label,
                expected_size=expected,
                resource=res,
            )
            distributions.append(
                databusclient.create_distribution(
                    url=url,
                    cvs=cvs,
                    file_format=_ckan_resource_file_format(res),
                    sha256_length_tuple=sha_tuple,
                )
            )

        artifact_name = dataset["name"]
        version = dataset.get("version") or dataset.get("metadata_modified")
        version_id = get_databus_identifier(group.name, artifact_name, version)
        title, abstract, description = sanitize_dataset_text_fields(
            _scalar_ckan_text(dataset.get("title")),
            _scalar_ckan_text(dataset.get("topic")),
            _scalar_ckan_text(dataset.get("notes")),
        )
        license_iri = normalize_ckan_license_for_databus(dataset)
        dataset = databusclient.create_dataset(
            version_id,
            title=title,
            abstract=abstract,
            description=description,
            license_url=license_iri,
            distributions=distributions,
            group_title=group.title,
            group_abstract=group.abstract,
            group_description=group.description,
        )
        return dataset
