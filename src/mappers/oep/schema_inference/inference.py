"""Orchestrate schema inference from remote tabular sources."""

from __future__ import annotations

import requests

from mappers.oep.schema_inference.errors import SchemaInferenceError
from mappers.oep.schema_inference.sample import (
    DEFAULT_FETCH_TIMEOUT_S,
    DEFAULT_SAMPLE_LINES,
    DEFAULT_SAMPLE_MAX_BYTES,
    TABULAR_FILE_EXTENSIONS,
    fetch_text_sample_from_url,
    is_tabular_file_format,
    sniff_delimiter,
)
from mappers.oep.schema_inference.schema_frictionless import SchemaFrictionless
from mappers.oep.schema_inference.schema_omi import SchemaOMI


class SchemaInference:
    """Infer OEMetadata schema and dialect from tabular file samples.

    Combines remote sample fetching with OMI-based inference and a Frictionless
    fallback when OMI fails.

    Attributes
    ----------
    omi : SchemaOMI
        OMI-backed schema inference backend.
    frictionless : SchemaFrictionless
        Frictionless-backed fallback backend.
    """

    TABULAR_FILE_EXTENSIONS = TABULAR_FILE_EXTENSIONS
    DEFAULT_SAMPLE_LINES = DEFAULT_SAMPLE_LINES
    DEFAULT_SAMPLE_MAX_BYTES = DEFAULT_SAMPLE_MAX_BYTES
    DEFAULT_FETCH_TIMEOUT_S = DEFAULT_FETCH_TIMEOUT_S

    is_tabular_file_format = staticmethod(is_tabular_file_format)
    sniff_delimiter = staticmethod(sniff_delimiter)

    def __init__(
        self,
        *,
        omi: SchemaOMI | None = None,
        frictionless: SchemaFrictionless | None = None,
    ):
        """Configure schema inference backends (OMI with Frictionless fallback).

        Parameters
        ----------
        omi : SchemaOMI or None, optional
            OMI backend instance (default: new :class:`SchemaOMI`).
        frictionless : SchemaFrictionless or None, optional
            Frictionless backend instance (default: new :class:`SchemaFrictionless`).
        """
        self.omi = omi or SchemaOMI()
        self.frictionless = frictionless or SchemaFrictionless()

    def fetch_text_sample_from_url(
        self,
        session: requests.Session,
        url: str,
        *,
        max_lines: int = DEFAULT_SAMPLE_LINES,
        max_bytes: int = DEFAULT_SAMPLE_MAX_BYTES,
        timeout: float = DEFAULT_FETCH_TIMEOUT_S,
        label: str | None = None,
    ) -> tuple[str, str]:
        """Stream the first lines of a remote text file without storing the full file.

        Parameters
        ----------
        session : requests.Session
            HTTP session used for the streaming GET request.
        url : str
            Remote URL of the tabular source file.
        max_lines : int, optional
            Maximum number of lines to read (default :data:`DEFAULT_SAMPLE_LINES`).
        max_bytes : int, optional
            Stop reading after this many bytes (default :data:`DEFAULT_SAMPLE_MAX_BYTES`).
        timeout : float, optional
            Request timeout in seconds (default :data:`DEFAULT_FETCH_TIMEOUT_S`).
        label : str or None, optional
            Display name for log messages; defaults to ``url``.

        Returns
        -------
        tuple[str, str]
            Sample text and detected delimiter from the first line.

        Raises
        ------
        SchemaInferenceError
            When the request fails or the fetched sample is empty.
        """
        return fetch_text_sample_from_url(
            session,
            url,
            max_lines=max_lines,
            max_bytes=max_bytes,
            timeout=timeout,
            label=label,
        )

    def infer_with_omi(self, sample_text: str, delimiter: str):
        """Infer schema using OMI.

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
        return self.omi.infer(sample_text, delimiter)

    def infer_with_frictionless(self, sample_text: str, delimiter: str):
        """Infer schema using Frictionless.

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
        return self.frictionless.infer(sample_text, delimiter)

    def infer_from_source_url(
        self,
        session: requests.Session,
        url: str,
        file_format: str,
        *,
        max_lines: int = DEFAULT_SAMPLE_LINES,
        prefer_omi: bool = True,
        label: str | None = None,
    ):
        """Download a short sample from a file URL and infer ``schema``.

        Parameters
        ----------
        session : requests.Session
            HTTP session used for the streaming GET request.
        url : str
            Remote URL of the tabular source file.
        file_format : str
            File extension or format token used to verify tabular support.
        max_lines : int, optional
            Maximum number of lines to read (default :data:`DEFAULT_SAMPLE_LINES`).
        prefer_omi : bool, optional
            When ``True``, try OMI first and fall back to Frictionless on failure
            (default ``True``). When ``False``, use Frictionless only.
        label : str or None, optional
            Display name for log messages; defaults to ``url``.

        Returns
        -------
        tuple[dict[str, Any], dict[str, str]]
            OEMetadata ``schema`` mapping and dialect hint.

        Raises
        ------
        SchemaInferenceError
            When ``file_format`` is not tabular or sample fetching fails.
        """
        if not self.is_tabular_file_format(file_format):
            raise SchemaInferenceError(
                f"Format {file_format!r} is not tabular; cannot infer schema from source URL."
            )
        sample, delimiter = self.fetch_text_sample_from_url(
            session,
            url,
            max_lines=max_lines,
            label=label,
        )
        try:
            if prefer_omi:
                return self.infer_with_omi(sample, delimiter)
            return self.infer_with_frictionless(sample, delimiter)
        except SchemaInferenceError:
            return self.infer_with_frictionless(sample, delimiter)
