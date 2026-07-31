"""Tests for the additive, language-neutral RIOPA adapter."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from fyi_archive.riopa_adapter import (
    CLASSIFICATIONS,
    build_adapter_report,
    canonical_sha256,
    load_json,
    resolve_json_pointer,
    validate_mapping,
    write_adapter_report,
)

ROOT = Path("conformance/riopa/v1")
MAPPING = ROOT / "fyi-archive-mapping.json"
FIXTURE = ROOT / "native-evidence-fixture.json"
REPORT = ROOT / "adapter-report.json"


def test_mapping_is_complete_and_references_native_evidence() -> None:
    mapping = load_json(MAPPING)
    fixture = load_json(FIXTURE)

    validate_mapping(mapping)

    assert mapping["repository"] == "edithatogo/fyi-archive"
    assert {item["classification"] for item in mapping["mappings"]} == CLASSIFICATIONS
    for item in mapping["mappings"]:
        filename, pointer = item["evidence_fixture"].split("#", maxsplit=1)
        assert filename == FIXTURE.name
        assert resolve_json_pointer(fixture, pointer) is not None


def test_report_preserves_fixture_and_is_deterministic() -> None:
    mapping = load_json(MAPPING)
    fixture = load_json(FIXTURE)

    first = build_adapter_report(mapping, fixture)
    second = build_adapter_report(copy.deepcopy(mapping), copy.deepcopy(fixture))

    assert first == second
    assert first["native_evidence_fixture"] == fixture
    assert first["fixture_sha256"] == canonical_sha256(fixture)
    assert first["mapping_sha256"] == canonical_sha256(mapping)
    assert set(first["classifications_present"]) == CLASSIFICATIONS
    for projection in first["projections"]:
        if projection["classification"] in {"exact", "approximate"}:
            assert projection["projected_value"] == projection["native_value"]
        else:
            assert projection["projected_value"] is None


def test_committed_report_matches_generator(tmp_path: Path) -> None:
    output = tmp_path / "adapter-report.json"

    write_adapter_report(mapping_path=MAPPING, fixture_path=FIXTURE, output_path=output)

    assert json.loads(output.read_text(encoding="utf-8")) == load_json(REPORT)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda mapping: mapping.pop("repository"), "missing required"),
        (
            lambda mapping: mapping["mappings"][0].update(classification="lossless"),
            "invalid mapping classification",
        ),
        (
            lambda mapping: mapping["mappings"][-1].update(riopa_field="snapshot.state"),
            "must not set riopa_field",
        ),
        (
            lambda mapping: mapping["mappings"][0].update(evidence_fixture="other.json#/value"),
            "unsupported evidence fixture",
        ),
    ],
)
def test_invalid_mapping_fails_closed(mutate, message: str) -> None:
    mapping = load_json(MAPPING)
    fixture = load_json(FIXTURE)
    mutate(mapping)

    with pytest.raises(ValueError, match=message):
        build_adapter_report(mapping, fixture)


def test_json_pointer_rejects_missing_and_scalar_traversal() -> None:
    with pytest.raises(ValueError, match="token not found"):
        resolve_json_pointer({"value": 1}, "/missing")
    with pytest.raises(ValueError, match="traverses scalar"):
        resolve_json_pointer({"value": 1}, "/value/nested")
