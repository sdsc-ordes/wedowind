"""Databus URI sanitization, text limits, and shared mapper CLI flags."""

import re
from argparse import ArgumentParser

from mappers.databus import (
    DATABUS_API_KEY_ENV,
    DATABUS_REGISTER_URL,
    DATABUS_TEXT_LIMITS,
    DATABUS_URI_BASE,
)


class GroupMetadata:
    """Databus group metadata attached to dataset JSON-LD payloads.

    Attributes
    ----------
    name : str
        Account/group path segment used in Databus version identifiers.
    title : str
        Human-readable group title.
    abstract : str
        Short abstract for the group.
    description : str
        Longer group description.

    Methods
    -------
    __init__(name, title, abstract, description)
        Store the four group fields on the instance.
    """

    def __init__(self, name: str, title: str, abstract: str, description: str):
        """Store Databus group fields used when building dataset payloads.

        Parameters
        ----------
        name : str
            Databus group slug / multi-segment account path for identifiers.
        title : str
            Group title.
        abstract : str
            Group abstract.
        description : str
            Group description.
        """
        self.name = name
        self.title = title
        self.abstract = abstract
        self.description = description


def sanitize_databus_uri_segment(value: str | None, *, fallback: str = "x") -> str:
    """Sanitize a single URI path segment for Databus identifier rules.

    Parameters
    ----------
    value : str or None
        Raw segment text.
    fallback : str, optional
        Returned when ``value`` is empty after stripping (default ``'x'``).

    Returns
    -------
    str
        Alphanumeric plus ``._+-`` with repeated hyphens collapsed.
    """
    raw = (value or "").strip()
    if not raw:
        return fallback
    safe = re.sub(r"[^a-zA-Z0-9._+\-]", "-", raw)
    safe = re.sub(r"-{2,}", "-", safe).strip("-")
    return safe or fallback


def normalize_databus_multi_segment_path(path_fragment: str | None) -> str:
    """Sanitize each slash-separated segment of an account/group path.

    Parameters
    ----------
    path_fragment : str or None
        Path such as ``wedowind/world-bank-group`` (leading/trailing slashes ignored).

    Returns
    -------
    str
        Slash-separated sanitized segments, or ``'account'`` when empty.
    """
    raw = str(path_fragment or "").strip().strip("/")
    if not raw:
        return "account"
    parts = [sanitize_databus_uri_segment(p, fallback="x") for p in raw.split("/") if p.strip()]
    return "/".join(parts) if parts else "account"


def get_databus_identifier(group_path: str, artifact_name: str, version: str | None = None):
    """Build the HTTPS Databus identifier for group_path/artifact[/version].

    group_path is typically the configured Databus group path, e.g. ``wedowind/zenodo``.
    """
    group_path_norm = normalize_databus_multi_segment_path(group_path)
    artifact_seg = sanitize_databus_uri_segment(artifact_name, fallback="artifact")
    identifier = f"{DATABUS_URI_BASE}/{group_path_norm}/{artifact_seg}"
    if version:
        identifier += f"/{sanitize_databus_uri_segment(version, fallback='v1')}"
    return identifier


def truncate_for_databus(value: str | None, field: str) -> str:
    """Truncate text to Databus SHACL limits for ``title``, ``abstract``, or ``description``.

    Parameters
    ----------
    value : str or None
        Raw text.
    field : str
        One of ``'title'``, ``'abstract'``, ``'description'`` (keys of
        :data:`mappers.databus.DATABUS_TEXT_LIMITS`).

    Returns
    -------
    str
        Stripped string truncated to the configured maximum length.

    Raises
    ------
    ValueError
        If ``field`` is not a known limit key.
    """
    max_length = DATABUS_TEXT_LIMITS.get(field)
    if max_length is None:
        raise ValueError(f"Unknown Databus field: {field}")

    text = (value or "").strip()
    if len(text) <= max_length:
        return text
    return text[:max_length]


def sanitize_dataset_text_fields(
    title: str | None, abstract: str | None, description: str | None
) -> tuple[str, str, str]:
    """Truncate title, abstract, and description to Databus limits.

    Parameters
    ----------
    title : str or None
        Dataset title.
    abstract : str or None
        Dataset abstract.
    description : str or None
        Dataset description.

    Returns
    -------
    tuple[str, str, str]
        ``(title, abstract, description)`` after truncation.
    """
    return (
        truncate_for_databus(title, "title"),
        truncate_for_databus(abstract, "abstract"),
        truncate_for_databus(description, "description"),
    )


def add_databus_publish_cli_args(parser: ArgumentParser) -> None:
    """Register ``--api-key`` and ``--register-url`` on an ArgumentParser.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Parser to extend in place.

    Returns
    -------
    None
    """
    parser.add_argument(
        "--api-key",
        default=None,
        help=f"Databus API key (or {DATABUS_API_KEY_ENV} env var).",
    )
    parser.add_argument(
        "--register-url",
        default=DATABUS_REGISTER_URL,
        help="Databus register endpoint.",
    )
