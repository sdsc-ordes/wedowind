"""Shared sample fetching and tabular file utilities."""

from __future__ import annotations

import os
import tempfile
from typing import Any

import requests

from mappers.oep.schema_inference.errors import SchemaInferenceError

TABULAR_FILE_EXTENSIONS = frozenset({"csv", "tsv", "txt"})
DEFAULT_SAMPLE_LINES = 2
DEFAULT_SAMPLE_MAX_BYTES = 256 * 1024
DEFAULT_FETCH_TIMEOUT_S = 120


def is_tabular_file_format(file_format: str | None) -> bool:
    """Return whether the format token is treated as CSV-like for inspection.

    Parameters
    ----------
    file_format : str or None
        File extension or format token (e.g. ``"csv"``, ``"tsv"``).

    Returns
    -------
    bool
        ``True`` when the format is empty or in :data:`TABULAR_FILE_EXTENSIONS`.
    """
    ext = (file_format or "").strip().lower()
    return ext in TABULAR_FILE_EXTENSIONS or ext == ""


def sniff_delimiter(header_line: str) -> str:
    """Guess CSV delimiter from the header line.

    Parameters
    ----------
    header_line : str
        First line of the sample text.

    Returns
    -------
    str
        Detected delimiter (``";"``, ``","``, ``"\\t"``, or ``"|"``), or ``","`` when none match.
    """
    for delim in (";", ",", "\t", "|"):
        if delim in header_line:
            return delim
    return ","


def write_sample_to_temp_csv(sample_text: str) -> str:
    """Write sample text to a temporary CSV file and return its path.

    Parameters
    ----------
    sample_text : str
        Tabular sample content to persist for inspection.

    Returns
    -------
    str
        Absolute path to the temporary ``.csv`` file (caller must delete it).
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".csv",
        delete=False,
    ) as tmp:
        tmp.write(sample_text)
        if not sample_text.endswith("\n"):
            tmp.write("\n")
        return tmp.name


def remove_temp_file(path: str | None) -> None:
    """Remove a temporary file when it exists.

    Parameters
    ----------
    path : str or None
        Path to the temporary file, or ``None`` (no-op).

    Returns
    -------
    None
    """
    if path and os.path.exists(path):
        os.unlink(path)


def dialect_hint(delimiter: str) -> dict[str, str]:
    """Build a standard OEMetadata dialect hint from a delimiter.

    Parameters
    ----------
    delimiter : str
        Field delimiter character used in the sample.

    Returns
    -------
    dict[str, str]
        OEMetadata dialect mapping with ``delimiter`` and ``decimalSeparator``.
    """
    return {"delimiter": delimiter, "decimalSeparator": "."}


def fetch_text_sample_from_url(
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
    name = label or url
    print(
        f"[oep:schema] Streaming first {max_lines} line(s) from source {name!r} …",
        flush=True,
    )
    try:
        with session.get(url, stream=True, timeout=timeout) as resp:
            resp.raise_for_status()
            lines: list[str] = []
            size = 0
            for raw in resp.iter_lines(decode_unicode=True):
                if raw is None:
                    continue
                line = raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")
                lines.append(line)
                size += len(line.encode("utf-8", errors="ignore")) + 1
                if len(lines) >= max_lines or size >= max_bytes:
                    break
    except requests.RequestException as err:
        raise SchemaInferenceError(f"Could not fetch sample from {url}: {err}") from err

    sample = "\n".join(lines).strip()
    if not sample:
        raise SchemaInferenceError(f"Empty sample from {url}")

    first_line = sample.splitlines()[0] if sample else ""
    delimiter = sniff_delimiter(first_line)
    print(
        f"[oep:schema] Sample size={len(sample)} bytes, delimiter={delimiter!r} (discarded after infer)",
        flush=True,
    )
    return sample, delimiter
