from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from fyi_archive.automation import automation_matrix, select_automation_targets
from fyi_archive.instances import get_instance, parse_instance_registry, resolve_instance

REGISTRY = Path("src/fyi_archive/config/archive_instances.json")
SCHEMA = Path("schemas/archive-instances.schema.json")

EXPECTED_POLICIES = {
    "ge-askgov": "Asia/Tbilisi",
    "se-handlingar": "Europe/Stockholm",
    "ua-dostup": "Europe/Kyiv",
    "uy-quesabes": "America/Montevideo",
}


def _documents() -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        json.loads(REGISTRY.read_text(encoding="utf-8")),
        json.loads(SCHEMA.read_text(encoding="utf-8")),
    )


def test_only_existing_working_sites_are_automation_enabled() -> None:
    targets = select_automation_targets()
    assert [target.instance.id for target in targets] == sorted(EXPECTED_POLICIES)
    assert {target.instance.id: target.policy.timezone for target in targets} == EXPECTED_POLICIES
    assert get_instance("nz-fyi").automation is None


def test_enabled_policies_preserve_existing_schedule_defaults() -> None:
    for target in select_automation_targets():
        assert target.policy.window_start_hour == 20
        assert target.policy.window_end_hour == 10
        assert target.policy.id_from == 1
        assert target.policy.id_to == 5
        assert target.policy.max_requests == 5
        assert target.policy.min_interval_seconds == 60
        assert target.policy.discovery_max_pages == 10


def test_matrix_is_stable_and_suitable_for_from_json() -> None:
    matrix = automation_matrix()
    assert [row["instance"] for row in matrix["include"]] == sorted(EXPECTED_POLICIES)
    assert matrix["include"][0] == {
        "instance": "ge-askgov",
        "timezone": "Asia/Tbilisi",
        "window_start_hour": 20,
        "window_end_hour": 10,
        "id_from": 1,
        "id_to": 5,
        "max_requests": 5,
        "min_interval_seconds": 60.0,
        "discovery_max_pages": 10,
    }


def test_matrix_script_emits_compact_json() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/build_alaveteli_automation_matrix.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert (
        result.stdout
        == json.dumps(automation_matrix(), separators=(",", ":"), sort_keys=True) + "\n"
    )


def test_schema_rejects_incomplete_automation_policy() -> None:
    document, schema = _documents()
    first = document["instances"][0]
    first["automation"] = {"enabled": True}
    with pytest.raises(ValueError, match="Invalid archive instance registry"):
        parse_instance_registry(document, schema)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("window_end_hour", 20, "window.*is empty"),
        ("id_from", 6, "id bounds.*must be ordered"),
    ],
)
def test_registry_rejects_invalid_automation_bounds(field: str, value: int, message: str) -> None:
    document, schema = _documents()
    automated = next(row for row in document["instances"] if row["id"] == "se-handlingar")
    automated["automation"][field] = value
    with pytest.raises(ValueError, match=message):
        parse_instance_registry(document, schema)


def test_instance_override_preserves_automation_identity() -> None:
    instance = resolve_instance(instance_id="se-handlingar", base_url="https://mirror.example.test")
    assert instance.automation == get_instance("se-handlingar").automation
