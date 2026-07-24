from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

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
    ("mutate", "message"),
    [
        (lambda payload: payload.update(schema_version="bad"), "unsupported Internet Archive"),
        (lambda payload: payload.update(defaults={}), "bounded Alaveteli request path"),
        (lambda payload: payload.update(targets=[]), "at least one target"),
        (lambda payload: payload.update(targets=["not-an-object"]), "target must be an object"),
        (
            lambda payload: payload.update(
                targets=[
                    {"instance_id": "invalid/id", "platform": "alaveteli", "host": "example.test"}
                ]
            ),
            "unique, URL-safe instance_id",
        ),
        (
            lambda payload: payload.update(
                targets=[{"instance_id": "test", "platform": "other", "host": "example.test"}]
            ),
            "explicitly classified as Alaveteli",
        ),
        (
            lambda payload: payload.update(
                targets=[
                    {"instance_id": "test", "platform": "alaveteli", "host": "example.test/path"}
                ]
            ),
            "bare hostname",
        ),
        (
            lambda payload: payload.update(
                targets=[
                    {
                        "instance_id": "test",
                        "platform": "alaveteli",
                        "host": "example.test",
                        "tier": 2,
                    }
                ]
            ),
            "Tier 1",
        ),
    ],
)
def test_registry_rejects_invalid_automated_target_contracts(
    tmp_path: Path, mutate: Callable[[dict[str, object]], None], message: str
) -> None:
    payload = cast(dict[str, object], json.loads(REGISTRY.read_text(encoding="utf-8")))
    mutate(payload)
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_registry(path)


def test_registry_rejects_non_alaveteli_target_that_is_capture_eligible(tmp_path: Path) -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    payload["non_alaveteli_targets"] = [
        {
            "instance_id": "example",
            "platform": "portal",
            "host": "example.test",
            "adapter_id": "portal-v1",
            "request_path_pattern": "/requests/*",
            "rights_review_status": "pending",
            "capture_eligible": True,
        }
    ]
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="catalogued only"):
        load_registry(path)
