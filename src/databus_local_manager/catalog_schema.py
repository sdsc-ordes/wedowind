"""Validation helpers for local per-group catalog JSON files."""

from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator

from databus_local_manager.logs import schemas_dir

_catalog_validator = Draft202012Validator(
    json.loads((schemas_dir() / "catalog.schema.json").read_text(encoding="utf-8"))
)


def validate_catalog_group(instance: dict[str, Any]) -> None:
    """Raise ``jsonschema.ValidationError`` if ``instance`` fails ``catalog.schema.json``."""
    _catalog_validator.validate(instance)
