from __future__ import annotations

import json
from pathlib import Path

import pytest

from fyi_archive.instances import list_instances
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
    assert all(item["capture_mode"] == "url_index" for item in matrix["include"])
    expected = {item.id for item in list_instances() if "internet_archive" in item.source_modes}
    assert {item["instance"] for item in matrix["include"]} == expected


def test_non_alaveteli_capture_requires_a_source_specific_adapter(tmp_path: Path) -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    payload["non_alaveteli_targets"] = [{"instance_id": "example", "platform": "portal"}]
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="platform-specific source adapter"):
        load_registry(path)


def test_matrix_can_select_one_registry_instance_for_manual_all_capture_runs() -> None:
    matrix = workflow_matrix(REGISTRY, instance_id="au-rtk", capture_mode="all_captures")

    assert matrix == {
        "include": [
            {
                "capture_mode": "all_captures",
                "host": "www.righttoknow.org.au",
                "instance": "au-rtk",
                "request_path": "/request/*",
            }
        ]
    }


def test_matrix_rejects_unknown_instance_or_capture_mode() -> None:
    with pytest.raises(ValueError, match="unknown registry instance"):
        workflow_matrix(REGISTRY, instance_id="not-configured")
    with pytest.raises(ValueError, match="unsupported CDX capture mode"):
        workflow_matrix(REGISTRY, capture_mode="all")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda payload: payload.update(schema_version="unsupported"), "unsupported"),
        (lambda payload: payload["defaults"].update(path_suffix="/anything/*"), "bounded"),
        (lambda payload: payload.update(targets=[]), "at least one"),
        (lambda payload: payload["targets"][0].update(instance_id="invalid_id"), "URL-safe"),
        (lambda payload: payload["targets"][0].update(platform="custom"), "Alaveteli"),
        (lambda payload: payload["targets"][0].update(host="example.test/path"), "bare hostname"),
        (lambda payload: payload["targets"][0].update(tier=2), "Tier 1"),
    ],
)
def test_registry_rejects_unsafe_automatic_target_contracts(
    tmp_path: Path, mutation, message: str
) -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    mutation(payload)
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_registry(path)
