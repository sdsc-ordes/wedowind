"""Infer OEMetadata schema using Frictionless."""

from __future__ import annotations

from typing import Any

from frictionless import Detector, Dialect, Resource
from frictionless.formats import CsvControl

from mappers.oep.schema_inference.errors import SchemaInferenceError
from mappers.oep.schema_inference.sample import (
    dialect_hint,
    remove_temp_file,
    write_sample_to_temp_csv,
)

FRICTIONLESS_TYPE_TO_OEM: dict[str, str] = {
    "string": "text",
    "integer": "integer",
    "number": "float",
    "boolean": "boolean",
    "date": "date",
    "datetime": "datetime",
    "year": "integer",
    "duration": "text",
    "time": "text",
    "any": "text",
}


def map_frictionless_type(frictionless_type: str | None) -> str:
    """Map a Frictionless field type to an OEMetadata field type.

    Parameters
    ----------
    frictionless_type : str or None
        Frictionless type token (e.g. ``"string"``, ``"integer"``).

    Returns
    -------
    str
        Corresponding OEMetadata type, or ``"text"`` when unmapped.
    """
    return FRICTIONLESS_TYPE_TO_OEM.get(str(frictionless_type or "string"), "text")


def frictionless_field_name(field: dict[str, Any]) -> str | None:
    """Return a non-empty field name or ``None`` when missing.

    Parameters
    ----------
    field : dict[str, Any]
        Frictionless field mapping.

    Returns
    -------
    str or None
        Stripped field name, or ``None`` when absent or blank.
    """
    name = str(field.get("name") or "").strip()
    return name or None


def frictionless_field_to_oem(field: dict[str, Any]) -> dict[str, Any] | None:
    """Map one Frictionless field dict to an OEMetadata field dict.

    Parameters
    ----------
    field : dict[str, Any]
        Frictionless field mapping with ``name`` and ``type``.

    Returns
    -------
    dict[str, Any] or None
        OEMetadata field mapping, or ``None`` when the name is missing or blank.
    """
    name = frictionless_field_name(field)
    if not name:
        return None
    return {
        "name": name,
        "description": "ToDo",
        "type": map_frictionless_type(field.get("type")),
        "nullable": True,
        "unit": None,
        "isAbout": [{"name": None, "@id": None}],
        "valueReference": [{"value": None, "name": None, "@id": None}],
    }


def guess_primary_key(oem_fields: list[dict[str, Any]]) -> list[str]:
    """Guess primary key when the first column is named ``id``.

    Parameters
    ----------
    oem_fields : list[dict[str, Any]]
        OEMetadata field mappings in column order.

    Returns
    -------
    list[str]
        ``["id"]`` when the first field name is ``id`` (case-insensitive), else ``[]``.
    """
    if oem_fields and oem_fields[0]["name"].lower() == "id":
        return ["id"]
    return []


def frictionless_fields_to_oem_schema(
    frictionless_fields: list[dict[str, Any]],
    *,
    delimiter: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Map Frictionless schema fields to OEMetadata ``schema`` and dialect.

    Parameters
    ----------
    frictionless_fields : list[dict[str, Any]]
        Frictionless field mappings from :func:`infer_fields`.
    delimiter : str
        Field delimiter character used in the sample.

    Returns
    -------
    tuple[dict[str, Any], dict[str, str]]
        OEMetadata ``schema`` mapping and dialect hint.
    """
    oem_fields: list[dict[str, Any]] = []
    for field in frictionless_fields:
        mapped = frictionless_field_to_oem(field)
        if mapped:
            oem_fields.append(mapped)
    schema = {
        "fields": oem_fields,
        "primaryKey": guess_primary_key(oem_fields),
        "foreignKeys": [],
    }
    return schema, dialect_hint(delimiter)


def build_csv_dialect(delimiter: str) -> Dialect:
    """Build a Frictionless CSV dialect for the given delimiter.

    Parameters
    ----------
    delimiter : str
        Field delimiter character.

    Returns
    -------
    Dialect
        Frictionless dialect with a :class:`~frictionless.formats.CsvControl`.
    """
    return Dialect(controls=[CsvControl(delimiter=delimiter)])


def build_detector() -> Detector:
    """Build the Frictionless detector used for schema inference.

    Returns
    -------
    Detector
        Detector with ``field_float_numbers=True``.
    """
    return Detector(field_float_numbers=True)


def build_resource(path: str, delimiter: str) -> Resource:
    """Build a Frictionless resource for a temp CSV sample.

    Parameters
    ----------
    path : str
        Absolute path to a local CSV sample file.
    delimiter : str
        Field delimiter character used in the sample.

    Returns
    -------
    Resource
        Configured tabular resource ready for :func:`infer_fields`.
    """
    return Resource(
        source=path,
        name="sample.csv",
        profile="tabular-data-resource",
        format="csv",
        dialect=build_csv_dialect(delimiter),
        detector=build_detector(),
    )


def infer_fields(resource: Resource) -> list[dict[str, Any]]:
    """Run Frictionless inference and return field dicts.

    Parameters
    ----------
    resource : Resource
        Frictionless tabular resource built via :func:`build_resource`.

    Returns
    -------
    list[dict[str, Any]]
        Non-empty list of Frictionless field mappings.

    Raises
    ------
    SchemaInferenceError
        When inference finds no columns in the sample.
    """
    resource.infer()
    fields = resource.schema.to_dict().get("fields") or []
    if not fields:
        raise SchemaInferenceError("Frictionless found no columns in sample.")
    return fields


class SchemaFrictionless:
    """Infer OEMetadata schema from tabular samples using Frictionless.

    Writes samples to a short-lived temp CSV, runs Frictionless schema
    inference, and maps field types to OEMetadata structures.

    Attributes
    ----------
    map_frictionless_type, frictionless_field_to_oem, frictionless_fields_to_oem_schema,
    build_csv_dialect, build_detector, build_resource, infer_fields
        Module-level helpers exposed as static methods on this class.
    """

    map_frictionless_type = staticmethod(map_frictionless_type)
    frictionless_field_to_oem = staticmethod(frictionless_field_to_oem)
    frictionless_fields_to_oem_schema = staticmethod(frictionless_fields_to_oem_schema)
    build_csv_dialect = staticmethod(build_csv_dialect)
    build_detector = staticmethod(build_detector)
    build_resource = staticmethod(build_resource)
    infer_fields = staticmethod(infer_fields)

    def infer_from_path(self, path: str, delimiter: str) -> tuple[dict[str, Any], dict[str, str]]:
        """Infer schema from a CSV file path.

        Parameters
        ----------
        path : str
            Absolute path to a local CSV sample file.
        delimiter : str
            Field delimiter character used in the sample.

        Returns
        -------
        tuple[dict[str, Any], dict[str, str]]
            OEMetadata ``schema`` mapping and dialect hint.

        Raises
        ------
        SchemaInferenceError
            When Frictionless finds no columns in the sample.
        """
        fields = self.infer_fields(self.build_resource(path, delimiter))
        return self.frictionless_fields_to_oem_schema(fields, delimiter=delimiter)

    def infer(self, sample_text: str, delimiter: str) -> tuple[dict[str, Any], dict[str, str]]:
        """Infer column schema using Frictionless on a short-lived temp CSV file.

        Parameters
        ----------
        sample_text : str
            Tabular sample content.
        delimiter : str
            Field delimiter used in the sample.

        Returns
        -------
        tuple[dict[str, Any], dict[str, str]]
            OEMetadata ``schema`` mapping and dialect hint.

        Raises
        ------
        SchemaInferenceError
            When Frictionless finds no columns in the sample.
        """
        tmp_path: str | None = None
        try:
            tmp_path = write_sample_to_temp_csv(sample_text)
            return self.infer_from_path(tmp_path, delimiter)
        finally:
            remove_temp_file(tmp_path)
