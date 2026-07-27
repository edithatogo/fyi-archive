from __future__ import annotations

import json
from pathlib import Path

import pytest

from fyi_archive.source_graph import build_source_graph, write_source_graph


def test_source_graph_covers_every_site_and_jurisdiction(tmp_path: Path) -> None:
    graph = write_source_graph(tmp_path / "graph.json")
    assert graph["counts"] == {
        "sites": 29,
        "jurisdiction_targets": 42,
        "preservation_sources": 9,
    }
    assert graph["transformation"]["lossless_join"] is True
    assert graph["transformation"]["inference"] == "none"
    assert len(graph["provenance"]["payload_sha256"]) == 64
    assert all(len(item["sha256"]) == 64 for item in graph["provenance"]["inputs"])
    assert all(
        site["internet_archive"]["discovery_status"] == "configured"
        and site["internet_archive"]["prospective_capture_status"]
        == "archive_it_or_equivalent_required"
        for site in graph["sites"]
    )
    assert json.loads((tmp_path / "graph.json").read_text()) == graph


def test_source_graph_rejects_unmapped_target(tmp_path: Path) -> None:
    config = json.loads(Path("configs/archive_source_graph.json").read_text())
    config["sites"][0]["jurisdiction_targets"] = ["NZ-OIA"]
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="jurisdiction mapping mismatch"):
        build_source_graph(config_path=path)


def test_source_graph_rejects_unknown_preservation_source(tmp_path: Path) -> None:
    config = json.loads(Path("configs/archive_source_graph.json").read_text())
    config["sites"][0]["additional_preservation_source_ids"] = ["unknown"]
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="unresolved preservation sources"):
        build_source_graph(config_path=path)
