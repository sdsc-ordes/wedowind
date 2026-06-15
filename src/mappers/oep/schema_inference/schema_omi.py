"""Infer OEMetadata schema using OMI."""

from __future__ import annotations

from typing import Any

from omi.inspection import InspectionError, infer_metadata

from mappers.oep.schema_inference.errors import SchemaInferenceError
from mappers.oep.schema_inference.sample import dialect_hint, remove_temp_file, write_sample_to_temp_csv


def run_omi_inspection(path: str) -> dict[str, Any]:
    """Run OMI ``infer_metadata`` on a local file path.

    Parameters
    ----------
    path : str
        Absolute path to a local tabular file (typically a temp CSV).

    Returns
    -------
    dict[str, Any]
        Full OMI metadata document for the file.

    Raises
    ------
    SchemaInferenceError
        When OMI raises :class:`~omi.inspection.InspectionError`.
    """
    try:
        return infer_metadata(path, "OEP")
    except InspectionError as err:
        raise SchemaInferenceError(str(err)) from err


def first_resource(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return the first resource dict from OMI metadata.

    Parameters
    ----------
    metadata : dict[str, Any]
        OMI metadata document returned by :func:`run_omi_inspection`.

    Returns
    -------
    dict[str, Any]
        First resource mapping, or an empty dict when none is present.
    """
    resources = metadata.get("resources")
    if isinstance(resources, list) and resources and isinstance(resources[0], dict):
        return resources[0]
    return {}


def extract_schema(metadata: dict[str, Any]) -> dict[str, Any]:
    """Extract the ``schema`` object from OMI metadata.

    Parameters
    ----------
    metadata : dict[str, Any]
        OMI metadata document returned by :func:`run_omi_inspection`.

    Returns
    -------
    dict[str, Any]
        Schema mapping from the first resource, or an empty dict when missing.
    """
    schema = first_resource(metadata).get("schema")
    return schema if isinstance(schema, dict) else {}


def extract_fields(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Return schema fields, raising when empty.

    Parameters
    ----------
    schema : dict[str, Any]
        OMI schema object extracted via :func:`extract_schema`.

    Returns
    -------
    list[dict[str, Any]]
        Non-empty list of field mappings.

    Raises
    ------
    SchemaInferenceError
        When ``schema`` has no ``fields`` list or it is empty.
    """
    fields = schema.get("fields")
    if not isinstance(fields, list) or not fields:
        raise SchemaInferenceError("OMI infer_metadata returned no fields.")
    return fields


def schema_to_oem_result(schema: dict[str, Any], delimiter: str) -> tuple[dict[str, Any], dict[str, str]]:
    """Build OEMetadata schema and dialect from an OMI schema object.

    Parameters
    ----------
    schema : dict[str, Any]
        OMI schema object with ``fields``, ``primaryKey``, and ``foreignKeys``.
    delimiter : str
        Field delimiter character used in the sample.

    Returns
    -------
    tuple[dict[str, Any], dict[str, str]]
        OEMetadata ``schema`` mapping and dialect hint.
    """
    return {
        "fields": schema.get("fields") or [],
        "primaryKey": schema.get("primaryKey") or [],
        "foreignKeys": schema.get("foreignKeys") or [],
    }, dialect_hint(delimiter)


class SchemaOMI:
    """Infer OEMetadata schema from tabular samples using OMI.

    Writes samples to a short-lived temp CSV, runs OMI inspection, and maps
    the result to OEMetadata ``schema`` and dialect structures.

    Attributes
    ----------
    run_omi_inspection, first_resource, extract_schema, extract_fields,
    schema_to_oem_result
        Module-level helpers exposed as static methods on this class.
    """

    run_omi_inspection = staticmethod(run_omi_inspection)
    first_resource = staticmethod(first_resource)
    extract_schema = staticmethod(extract_schema)
    extract_fields = staticmethod(extract_fields)
    schema_to_oem_result = staticmethod(schema_to_oem_result)

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
            When OMI inspection fails or returns no fields.
        """
        metadata = self.run_omi_inspection(path)
        schema = self.extract_schema(metadata)
        self.extract_fields(schema)
        return self.schema_to_oem_result(schema, delimiter)

    def infer(self, sample_text: str, delimiter: str) -> tuple[dict[str, Any], dict[str, str]]:
        """Infer schema via OMI (temp file deleted immediately after).

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
            When OMI inspection fails or returns no fields.
        """
        tmp_path: str | None = None
        try:
            tmp_path = write_sample_to_temp_csv(sample_text)
            return self.infer_from_path(tmp_path, delimiter)
        finally:
            remove_temp_file(tmp_path)
