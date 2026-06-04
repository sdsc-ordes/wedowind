from __future__ import annotations

from mappers.oep.oep_table import OepTable
from mappers.oep.sanitize import cut_oep_identifier, sanitize_oep_identifier


def test_sanitize_oep_identifier() -> None:
    """Sanitize strips punctuation and lowercases identifiers."""
    assert sanitize_oep_identifier("My File-Name.csv") == "my_file_name_csv"


def test_build_oep_table_name_respects_max_length() -> None:
    """Table names are truncated to the configured maximum length."""
    name = OepTable.build_oep_table_name(
        prefix="p",
        source_key="source",
        dataset_key="dataset_with_a_very_long_name",
        resource_key="resource_with_a_very_long_name",
        max_length=40,
    )
    assert len(name) <= 40
    assert name.startswith("p_")


def test_cut_oep_identifier_uses_stable_suffix() -> None:
    """Long identifiers get a deterministic hash suffix when truncated."""
    raw = "wedowind_community_wedowind_5946808_penmanshiel_wt_datasignalma"
    cut = cut_oep_identifier(raw, max_length=50)
    assert len(cut) <= 50
    assert cut != raw
    assert "_" in cut
