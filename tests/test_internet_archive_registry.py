from __future__ import annotations

import json
from pathlib import Path

import pytest

from fyi_archive.internet_archive_registry import load_registry, workflow_matrix

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "configs/historical/internet_archive_sources.json"
SCHEMA = ROOT / "schemas/internet-archive-source-registry.schema.json"


def test_registry_is_valid_and_exposes_only_alaveteli_capture_targets() -> None:
    registry = load_registry(REGISTRY)
    matrix = workflow_matrix(REGISTRY)

    assert json.loads(SCHEMA.read_text(encoding="utf-8"))["$schema"].endswith("schema")
    assert registry["gates"]["publication"] is False
    assert {item["instance"] for item in matrix["include"]} >= {"au-rtk", "uk-wdtk"}
    assert all(item["request_path"] == "/request/*" for item in matrix["include"])


def test_non_alaveteli_capture_requires_a_source_specific_adapter(tmp_path: Path) -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    payload["non_alaveteli_targets"] = [{"instance_id": "example", "platform": "portal"}]
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="platform-specific source adapter"):
        load_registry(path)
