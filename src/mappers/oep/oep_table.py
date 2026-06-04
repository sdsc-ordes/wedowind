"""OEP table definition and REST API provisioning."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any

import requests
from omi.settings import OEP_URL

from mappers.oep.sanitize import (
    MAX_OEP_IDENTIFIER_LEN,
    cut_oep_identifier,
    sanitize_oep_identifier,
)
from mappers.oep.schema_inference import SchemaInference

OEP_TABLE_TIMEOUT_S = 90
MAX_OEP_COLUMN_NAME_LEN = 63

OEM_FIELD_TYPE_TO_OEP_DATA_TYPE: dict[str, str] = {
    "text": "text",
    "string": "text",
    "integer": "bigint",
    "float": "float",
    "number": "float",
    "boolean": "boolean",
    "date": "date",
    "datetime": "datetime",
    "serial": "bigint",
    "geometry": "geometry",
    "geojson": "geometry",
}


class OepTableProvisionError(RuntimeError):
    """Raised when OEP table creation fails via the REST API."""


@dataclass
class OepColumn:
    """One column in an OEP table definition.

    Attributes
    ----------
    name : str
        Column identifier.
    data_type : str
        OEP data type token (e.g. ``text``, ``bigint``, ``bigserial``).
    primary_key : bool, optional
        Whether this column is the primary key. Default is ``False``.
    is_nullable : bool or None, optional
        Explicit nullability for the API; ``None`` omits the field from the
        payload. Default is ``None``.
    """

    name: str
    data_type: str
    primary_key: bool = False
    is_nullable: bool | None = None

    def build_api_dict(self) -> dict[str, Any]:
        """Serialize to an OEP table column definition for the REST API.

        Returns
        -------
        dict[str, Any]
            Column definition with ``name``, ``data_type``, and optional
            ``primary_key`` / ``is_nullable`` keys.
        """
        column: dict[str, Any] = {"name": self.name, "data_type": self.data_type}
        if self.primary_key:
            column["primary_key"] = True
        if self.is_nullable is False:
            column["is_nullable"] = False
        return column


@dataclass
class OepTable:
    """OEP table composed of a name, OEMetadata schema, and API column definitions.

    Attributes
    ----------
    name : str
        OEP table identifier.
    schema : dict[str, Any]
        OEMetadata-compatible schema (``fields``, ``primaryKey``, etc.).
    format : str, optional
        File format label stored on the resource. Default is ``"CSV"``.
    columns : list[OepColumn], optional
        Column definitions sent to the OEP tables API. Default is an empty
        list.
    """

    name: str
    schema: dict[str, Any]
    format: str = "CSV"
    columns: list[OepColumn] = field(default_factory=list)

    OEM_FIELD_TYPE_TO_OEP_DATA_TYPE = OEM_FIELD_TYPE_TO_OEP_DATA_TYPE
    MAX_COLUMN_NAME_LEN = MAX_OEP_COLUMN_NAME_LEN
    MAX_NAME_LEN = MAX_OEP_IDENTIFIER_LEN
    API_TIMEOUT_S = OEP_TABLE_TIMEOUT_S

    @classmethod
    def build_oep_table_name(
        cls,
        *,
        prefix: str,
        source_key: str,
        dataset_key: str,
        resource_key: str,
        max_length: int = MAX_OEP_IDENTIFIER_LEN,
    ) -> str:
        """Build a deterministic OEP table name from source and resource keys.

        Parameters
        ----------
        prefix : str
            Configured table name prefix (e.g. ``"wd"``).
        source_key : str
            Identifier for the upstream data source.
        dataset_key : str
            Identifier for the dataset within the source.
        resource_key : str
            Identifier for the resource within the dataset.
        max_length : int, optional
            Maximum length of the resulting name. Default is
            ``MAX_OEP_IDENTIFIER_LEN``.

        Returns
        -------
        str
            Sanitized, truncated table name.
        """
        parts = [
            sanitize_oep_identifier(prefix, fallback="wd"),
            sanitize_oep_identifier(source_key, fallback="src"),
            sanitize_oep_identifier(dataset_key, fallback="ds"),
            sanitize_oep_identifier(resource_key, fallback="res"),
        ]
        name = "_".join(p for p in parts if p)
        return cut_oep_identifier(name, max_length=max_length)

    @staticmethod
    def build_auth_headers(token: str) -> dict[str, str]:
        """Build OEP REST API authorization headers.

        Parameters
        ----------
        token : str
            OEP API token.

        Returns
        -------
        dict[str, str]
            Headers including ``Authorization``, ``Content-Type``, and
            ``Accept``.
        """
        return {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @classmethod
    def get_api_url_for(cls, table_name: str) -> str:
        """Return the OEP tables API URL for a table name.

        Parameters
        ----------
        table_name : str
            OEP table identifier.

        Returns
        -------
        str
            Full URL for ``GET``/``PUT /api/v0/tables/{table_name}/``.
        """
        return f"{OEP_URL}/api/v0/tables/{table_name}/"

    @classmethod
    def sanitize_column_name(cls, value: str | None, *, fallback: str = "column") -> str:
        """Normalize a column name for OEP SQL identifier constraints.

        Parameters
        ----------
        value : str or None
            Raw column name from OEMetadata or upstream source.
        fallback : str, optional
            Name used when ``value`` is empty or sanitizes to nothing.
            Default is ``"column"``.

        Returns
        -------
        str
            Lowercase alphanumeric identifier, prefixed with ``c_`` when
            needed, truncated to ``MAX_COLUMN_NAME_LEN``.
        """
        raw = (value or "").strip().lower()
        safe = re.sub(r"[^a-z0-9]+", "_", raw)
        safe = re.sub(r"_+", "_", safe).strip("_")
        if not safe:
            safe = fallback
        if not safe[0].isalpha():
            safe = f"c_{safe}"
        return safe[:cls.MAX_COLUMN_NAME_LEN].rstrip("_") or "column"

    @classmethod
    def sanitize_schema(cls, schema: dict[str, Any]) -> dict[str, Any]:
        """Return schema copy with OEP-safe, unique ``fields[].name`` values.

        Parameters
        ----------
        schema : dict[str, Any]
            OEMetadata schema dict containing a ``fields`` list.

        Returns
        -------
        dict[str, Any]
            Deep copy of ``schema`` with sanitized, deduplicated field names.
        """
        out = copy.deepcopy(schema) if isinstance(schema, dict) else {}
        fields = out.get("fields")
        if not isinstance(fields, list):
            out["fields"] = []
            return out

        used: set[str] = set()
        for idx, field_def in enumerate(fields, start=1):
            if not isinstance(field_def, dict):
                continue
            base = cls.sanitize_column_name(
                str(field_def.get("name") or ""), fallback=f"column_{idx}"
            )
            name = base
            suffix = 1
            while name in used:
                tag = f"_{suffix}"
                budget = cls.MAX_COLUMN_NAME_LEN - len(tag)
                stem = base[:budget].rstrip("_") or "column"
                name = f"{stem}{tag}"
                suffix += 1
            field_def["name"] = name
            used.add(name)
        return out

    @classmethod
    def build_minimal_placeholder_schema(cls) -> dict[str, Any]:
        """Schema for non-tabular sources: OEP table with auto ``id`` only.

        Returns
        -------
        dict[str, Any]
            Empty ``fields`` list with ``primaryKey`` set to ``["id"]``.
        """
        return {"fields": [], "primaryKey": ["id"], "foreignKeys": []}

    @classmethod
    def map_oem_field_type(cls, oem_type: str | None) -> str:
        """Map an OEMetadata field type to an OEP ``data_type`` token.

        Parameters
        ----------
        oem_type : str or None
            OEMetadata field ``type`` value.

        Returns
        -------
        str
            OEP data type token; defaults to ``"text"`` for unknown types.
        """
        return cls.OEM_FIELD_TYPE_TO_OEP_DATA_TYPE.get(str(oem_type or "text").lower(), "text")

    @classmethod
    def build_column_from_oem_field(cls, field_def: dict[str, Any]) -> OepColumn | None:
        """Convert one OEMetadata schema field to an ``OepColumn``.

        Parameters
        ----------
        field_def : dict[str, Any]
            Single OEMetadata ``schema.fields`` entry.

        Returns
        -------
        OepColumn or None
            Column definition, or ``None`` when the field has no name.
        """
        name = str(field_def.get("name") or "").strip()
        if not name:
            return None
        data_type = cls.map_oem_field_type(field_def.get("type"))
        primary_key = name.lower() == "id"
        if primary_key and data_type == "bigint":
            data_type = "bigserial"
        nullable = field_def.get("nullable")
        is_nullable = None if nullable is not False else False
        return OepColumn(
            name=name,
            data_type=data_type,
            primary_key=primary_key,
            is_nullable=is_nullable,
        )

    @classmethod
    def build_columns_from_schema(cls, schema: dict[str, Any]) -> list[OepColumn]:
        """Convert OEMetadata ``schema.fields`` to OEP column definitions.

        Parameters
        ----------
        schema : dict[str, Any]
            OEMetadata schema dict.

        Returns
        -------
        list[OepColumn]
            Column list including an auto ``id`` column when missing from
            ``schema.fields``.
        """
        normalized_schema = cls.sanitize_schema(schema)
        fields = (
            normalized_schema.get("fields")
            if isinstance(normalized_schema.get("fields"), list)
            else []
        )
        columns: list[OepColumn] = []
        has_id = any(
            isinstance(field_def, dict) and str(field_def.get("name") or "").lower() == "id"
            for field_def in fields
        )

        if not has_id:
            columns.append(OepColumn(name="id", data_type="bigserial", primary_key=True))

        for field_def in fields:
            if not isinstance(field_def, dict):
                continue
            column = cls.build_column_from_oem_field(field_def)
            if column:
                columns.append(column)

        if not columns:
            columns = [OepColumn(name="id", data_type="bigserial", primary_key=True)]
        return columns

    @classmethod
    def build_from_oemetadata(
        cls,
        *,
        name: str,
        schema: dict[str, Any],
        file_format: str = "csv",
    ) -> OepTable:
        """Build an OEP table from OEMetadata resource fields.

        Parameters
        ----------
        name : str
            OEP table identifier.
        schema : dict[str, Any]
            OEMetadata ``schema`` object.
        file_format : str, optional
            Resource file format label. Default is ``"csv"``.

        Returns
        -------
        OepTable
            Table with sanitized schema and derived columns.
        """
        sanitized_schema = cls.sanitize_schema(schema)
        return cls(
            name=name,
            schema=sanitized_schema,
            format=(file_format or "txt").upper()[:32],
            columns=cls.build_columns_from_schema(sanitized_schema),
        )

    @classmethod
    def build_from_oemetadata_dict(cls, resource: dict[str, Any]) -> OepTable:
        """Build an OEP table from one OEMetadata resource dict.

        Parameters
        ----------
        resource : dict[str, Any]
            OEMetadata ``resources`` entry with ``name``, ``schema``, and
            ``format`` keys.

        Returns
        -------
        OepTable
            Table built from the resource fields.
        """
        return cls.build_from_oemetadata(
            name=str(resource.get("name") or "").strip(),
            schema=resource.get("schema") if isinstance(resource.get("schema"), dict) else {},
            file_format=str(resource.get("format") or "csv"),
        )

    def get_api_url(self) -> str:
        """Return this table's OEP REST API URL.

        Returns
        -------
        str
            Full URL for ``GET``/``PUT /api/v0/tables/{name}/``.
        """
        return self.get_api_url_for(self.name)

    def build_put_payload(self) -> dict[str, Any]:
        """Build the JSON body for ``PUT /api/v0/tables/{name}/``.

        Returns
        -------
        dict[str, Any]
            Payload with ``query.columns`` listing serialized column
            definitions.
        """
        return {"query": {"columns": [column.build_api_dict() for column in self.columns]}}

    def exists(self, session: requests.Session, *, token: str) -> bool:
        """Return whether the OEP table already exists.

        Parameters
        ----------
        session : requests.Session
            HTTP session used for the API request.
        token : str
            OEP API token.

        Returns
        -------
        bool
            ``True`` when the table endpoint responds with HTTP 200.
        """
        resp = session.get(
            self.get_api_url(),
            headers=self.build_auth_headers(token),
            timeout=self.API_TIMEOUT_S,
        )
        return resp.status_code == 200

    def create(self, session: requests.Session, *, token: str) -> None:
        """Create an empty OEP table via ``PUT /api/v0/tables/{name}/``.

        Parameters
        ----------
        session : requests.Session
            HTTP session used for the API request.
        token : str
            OEP API token.

        Returns
        -------
        None

        Raises
        ------
        OepTableProvisionError
            If the OEP API returns a non-success status code.
        """
        print(
            f"[oep:table] PUT empty table {self.name!r} ({len(self.columns)} columns) …",
            flush=True,
        )
        resp = session.put(
            self.get_api_url(),
            json=self.build_put_payload(),
            headers=self.build_auth_headers(token),
            timeout=self.API_TIMEOUT_S,
        )
        if not resp.ok:
            raise OepTableProvisionError(
                f"Could not create OEP table {self.name!r}: {resp.status_code} {resp.text}"
            )
        print(f"[oep:table] Created empty table {self.name!r}", flush=True)

    @classmethod
    def ensure_for_metadata(
        cls,
        session: requests.Session,
        metadata: dict[str, Any],
        *,
        token: str,
        schema_inference: SchemaInference | None = None,
        dry_run: bool = False,
        skip_existing: bool = True,
    ) -> list[str]:
        """Ensure each ``resources[].name`` table exists on the OEP before metadata push.

        Parameters
        ----------
        session : requests.Session
            HTTP session used for OEP API requests.
        metadata : dict[str, Any]
            Full OEMetadata document; ``resources`` is read and may be
            mutated in place (``schema`` updates).
        token : str
            OEP API token.
        schema_inference : SchemaInference or None, optional
            Used to detect non-tabular formats needing a placeholder schema.
            Default is a new ``SchemaInference`` instance.
        dry_run : bool, optional
            When ``True``, log actions without calling the API. Default is
            ``False``.
        skip_existing : bool, optional
            When ``True``, skip ``PUT`` for tables that already exist.
            Default is ``True``.

        Returns
        -------
        list[str]
            Table names that were ensured (created, skipped, or dry-run).

        Raises
        ------
        OepTableProvisionError
            If ``metadata`` has no ``resources`` list.
        """
        inference = schema_inference or SchemaInference()
        resources = metadata.get("resources")
        if not isinstance(resources, list):
            raise OepTableProvisionError("Metadata has no resources list.")

        ensured: list[str] = []
        for res in resources:
            if not isinstance(res, dict):
                continue
            table_name = (res.get("name") or "").strip()
            if not table_name:
                continue
            schema = res.get("schema") if isinstance(res.get("schema"), dict) else {}
            fmt = str(res.get("format") or "csv")

            if dry_run:
                n_fields = len(schema.get("fields") or [])
                print(
                    f"[oep:table] dry-run: would ensure table {table_name!r} "
                    f"({n_fields} data columns + OEP id)",
                    flush=True,
                )
                ensured.append(table_name)
                continue

            table = cls.build_from_oemetadata_dict(res)

            if skip_existing and table.exists(session, token=token):
                print(f"[oep:table] Table {table_name!r} already exists; skip create", flush=True)
                ensured.append(table_name)
                continue

            if not inference.is_tabular_file_format(fmt) and not schema.get("fields"):
                table = cls.build_from_oemetadata(
                    name=table_name,
                    schema=cls.build_minimal_placeholder_schema(),
                    file_format=fmt,
                )

            res["schema"] = table.schema

            try:
                table.create(session, token=token)
            except OepTableProvisionError:
                continue
            ensured.append(table_name)

        return ensured
