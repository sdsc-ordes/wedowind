from __future__ import annotations

import pytest

from databus_manager.handle_jsonld import (
    get_graph_node,
    version_id_to_artefact_id,
    version_id_to_group_id,
)


def test_get_graph_node_by_type_and_type_list() -> None:
    doc = {"@graph": [{"@type": ["Thing", "Group"], "title": "x"}]}
    node = get_graph_node(doc, "Group")
    assert node["title"] == "x"


def test_get_graph_node_raises_when_graph_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid @graph"):
        get_graph_node({"@graph": {}}, "Group")


def test_get_graph_node_raises_when_missing_type() -> None:
    with pytest.raises(ValueError, match="No @graph node"):
        get_graph_node({"@graph": [{"@type": "Group"}]}, "Version")


def test_version_id_to_group_and_artefact() -> None:
    version_id = "https://databus.openenergyplatform.org/wedowind/zenodo/example-artefact-one/v1.0.0"
    assert (
        version_id_to_group_id(version_id)
        == "https://databus.openenergyplatform.org/wedowind/zenodo"
    )
    assert (
        version_id_to_artefact_id(version_id)
        == "https://databus.openenergyplatform.org/wedowind/zenodo/example-artefact-one"
    )
