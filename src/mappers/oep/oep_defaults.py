"""OEP publishing defaults loaded from mapper source configuration."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

DEFAULT_OEP_CONTEXT = (
    "https://raw.githubusercontent.com/OpenEnergyPlatform/oemetadata/"
    "production/oemetadata/latest/context.json"
)
DEFAULT_METADATA_VERSION = "OEMetadata-2.0.4"
DEFAULT_TOPIC = "wind"
DEFAULT_LANGUAGES = ("en-GB",)
DEFAULT_SUBJECT = {
    "name": "energy",
    "@id": "https://openenergyplatform.org/ontology/oeo/OEO_00000150",
}
DEFAULT_PUBLISHER = "WeDoWind"


@dataclass
class OepDefaults:
    """OEP-specific defaults for OEMetadata generation.

    Attributes
    ----------
    topic : tuple[str, ...]
        OEP schema topics (e.g. ``model_draft``).
    table_prefix : str
        Prefix for generated OEP table names.
    languages : tuple[str, ...]
        BCP47 language tags for resources.
    subject : dict[str, str]
        Default ontology subject (``name``, ``@id``).
    publisher : str
        Default ``context.publisher`` string.
    metadata_version : str
        ``metaMetadata.metadataVersion`` value.
    provenance_label : str
        Short label stored in resource keywords (e.g. ``zenodo``, ``ckan``).
    infer_schema : bool
        When True, download a few lines from each source file URL to infer ``schema.fields``.
    schema_sample_lines : int
        Lines to stream from Zenodo/CKAN files (header + data); not stored on disk.
    ensure_tables : bool
        When True, create empty OEP tables (PUT schema, no data rows) before metadata push.
    """

    topic: tuple[str, ...] = (DEFAULT_TOPIC,)
    table_prefix: str = "wedowind_"
    languages: tuple[str, ...] = DEFAULT_LANGUAGES
    subject: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_SUBJECT))
    publisher: str = DEFAULT_PUBLISHER
    metadata_version: str = DEFAULT_METADATA_VERSION
    provenance_label: str = "external"
    infer_schema: bool = True
    schema_sample_lines: int = 2
    ensure_tables: bool = True


def _coerce_str_list(value: Any, *, fallback: tuple[str, ...]) -> tuple[str, ...]:
    """Coerce config values to a non-empty tuple of strings.

    Parameters
    ----------
    value : Any
        Config value: a single string, list of strings, or other type.
    fallback : tuple[str, ...]
        Returned when ``value`` cannot be coerced to a non-empty tuple.

    Returns
    -------
    tuple[str, ...]
        Stripped non-empty strings.
    """
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    if isinstance(value, list):
        items = [str(v).strip() for v in value if v is not None and str(v).strip()]
        if items:
            return tuple(items)
    return fallback


def parse_oep_defaults(section: dict[str, Any] | None, *, provenance_label: str) -> OepDefaults:
    """Parse an ``oep`` object from mapper ``defaults`` or source config.

    Parameters
    ----------
    section : dict or None
        ``defaults.oep`` or source-level ``oep`` mapping.
    provenance_label : str
        Value for :attr:`OepDefaults.provenance_label` when not overridden.

    Returns
    -------
    OepDefaults
        Parsed defaults with fallbacks for missing keys.
    """
    data = section if isinstance(section, dict) else {}
    subject_raw = data.get("subject")
    subject = dict(DEFAULT_SUBJECT)
    if isinstance(subject_raw, dict):
        if isinstance(subject_raw.get("name"), str) and subject_raw["name"].strip():
            subject["name"] = subject_raw["name"].strip()
        if isinstance(subject_raw.get("@id"), str) and subject_raw["@id"].strip():
            subject["@id"] = subject_raw["@id"].strip()

    prefix = data.get("table_prefix") or data.get("prefix") or "wedowind_"
    publisher = data.get("publisher") or DEFAULT_PUBLISHER
    version = data.get("metadata_version") or DEFAULT_METADATA_VERSION
    label = data.get("provenance_label") or provenance_label

    infer_schema = data.get("infer_schema", True)
    if isinstance(infer_schema, str):
        infer_schema = infer_schema.strip().lower() not in ("0", "false", "no")

    ensure_tables = data.get("ensure_tables", True)
    if isinstance(ensure_tables, str):
        ensure_tables = ensure_tables.strip().lower() not in ("0", "false", "no")

    sample_lines = data.get("schema_sample_lines", 2)
    try:
        schema_sample_lines = max(1, min(int(sample_lines), 20))
    except (TypeError, ValueError):
        schema_sample_lines = 2

    return OepDefaults(
        topic=_coerce_str_list(data.get("topic") or data.get("topics"), fallback=(DEFAULT_TOPIC,)),
        table_prefix=str(prefix).strip() or "wedowind_",
        languages=_coerce_str_list(data.get("languages"), fallback=DEFAULT_LANGUAGES),
        subject=subject,
        publisher=str(publisher).strip() or DEFAULT_PUBLISHER,
        metadata_version=str(version).strip() or DEFAULT_METADATA_VERSION,
        provenance_label=str(label).strip() or provenance_label,
        infer_schema=bool(infer_schema),
        schema_sample_lines=schema_sample_lines,
        ensure_tables=bool(ensure_tables),
    )


def apply_oep_cli_overrides(oep: OepDefaults, args: Any) -> OepDefaults:
    """Apply OEP-related CLI flags to parsed defaults.

    Reads ``--no-infer-schema``, ``--no-provision-tables``, and
    ``--schema-sample-lines`` from ``args`` when present.

    Parameters
    ----------
    oep : OepDefaults
        Base defaults from config.
    args : Any
        Parsed argparse namespace (typically from publish CLI).

    Returns
    -------
    OepDefaults
        Copy with CLI overrides applied, or ``oep`` unchanged when no flags
        are set.
    """
    kw: dict[str, Any] = {}
    if getattr(args, "no_infer_schema", False):
        kw["infer_schema"] = False
    if getattr(args, "no_provision_tables", False):
        kw["ensure_tables"] = False
    sample_lines = getattr(args, "schema_sample_lines", None)
    if sample_lines is not None:
        try:
            kw["schema_sample_lines"] = max(1, min(int(sample_lines), 20))
        except (TypeError, ValueError):
            pass
    return replace(oep, **kw) if kw else oep
