from __future__ import annotations

import pytest

from mappers.oep.oep_table import OepTable, OepTableProvisionError
from mappers.oep.schema_inference import SchemaFrictionless, SchemaInference

schema_inference = SchemaInference()
schema_frictionless = SchemaFrictionless()


def test_sniff_delimiter() -> None:
    """Delimiter sniffing prefers semicolons over commas when both appear."""
    assert schema_inference.sniff_delimiter("a;b;c") == ";"
    assert schema_inference.sniff_delimiter("a,b,c") == ","


def test_is_tabular() -> None:
    """Tabular format detection recognizes csv-like extensions."""
    assert schema_inference.is_tabular_file_format("csv")
    assert not schema_inference.is_tabular_file_format("zip")


def test_infer_schema_from_two_line_csv_sample() -> None:
    """Frictionless infers column names from a two-line CSV sample."""
    sample = "name,capacity_mw\nunit1,1.2\n"
    schema, dialect = schema_frictionless.infer(sample, ",")
    names = [f["name"] for f in schema["fields"]]
    assert "name" in names
    assert "capacity_mw" in names
    assert dialect["delimiter"] == ","


def test_oep_columns_adds_bigserial_id() -> None:
    """OEP columns always include an auto-increment ``id`` when missing."""
    schema = {
        "fields": [
            {"name": "name", "type": "text", "nullable": True},
            {"name": "capacity_mw", "type": "float", "nullable": True},
        ],
        "primaryKey": [],
    }
    table = OepTable.build_from_oemetadata(name="placeholder", schema=schema)
    columns = [column.build_api_dict() for column in table.columns]
    assert columns[0]["name"] == "id"
    assert columns[0]["data_type"] == "bigserial"
    assert any(c["name"] == "capacity_mw" for c in columns)


def test_sanitize_oep_column_name_enforces_oep_identifier_rules() -> None:
    """Column names are lowercased, underscored, and prefixed when needed."""
    name = OepTable.sanitize_column_name("Wind Farm,Title,Alternative Title")
    assert name == "wind_farm_title_alternative_title"

    numeric = OepTable.sanitize_column_name("2024 value")
    assert numeric.startswith("c_")


def test_sanitize_oemetadata_schema_makes_unique_names() -> None:
    """Schema sanitization deduplicates conflicting field names."""
    schema = {
        "fields": [
            {"name": "Wind Farm,Title"},
            {"name": "wind_farm_title"},
            {"name": "123"},
        ]
    }
    sanitized = OepTable.sanitize_schema(schema)
    names = [f["name"] for f in sanitized["fields"]]
    assert len(set(names)) == len(names)
    assert names[0] == "wind_farm_title"
    assert names[1].startswith("wind_farm_title_")
    assert names[2].startswith("c_")


def test_ensure_for_metadata_continues_after_table_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Table provisioning skips failed tables and continues with the rest."""
    metadata = {
        "resources": [
            {"name": "ok_table", "format": "csv", "schema": {"fields": [{"name": "a"}]}},
            {"name": "bad_table", "format": "csv", "schema": {"fields": [{"name": "b"}]}},
        ]
    }

    monkeypatch.setattr(OepTable, "exists", lambda self, *args, **kwargs: False)

    def _fake_create(self, session, *, token):
        """Simulate table creation failure for one table name."""
        if self.name == "bad_table":
            raise OepTableProvisionError("boom")

    monkeypatch.setattr(OepTable, "create", _fake_create)

    ensured = OepTable.ensure_for_metadata(object(), metadata, token="t")
    assert ensured == ["ok_table"]
