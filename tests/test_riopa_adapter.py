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


def test_load_json_rejects_non_object_root(tmp_path: Path) -> None:
    path = tmp_path / "array.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain a JSON object"):
        load_json(path)


@pytest.mark.parametrize(
    ("document", "pointer", "message"),
    [
        ({"items": []}, "items/0", "invalid JSON Pointer"),
        ({"items": []}, "/items/0", "invalid JSON Pointer array index"),
        ({"items": ["only"]}, "/items/not-an-index", "invalid JSON Pointer array index"),
    ],
)
def test_json_pointer_rejects_invalid_syntax_and_indexes(
    document: object, pointer: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        resolve_json_pointer(document, pointer)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda mapping: mapping.update(schema_version="2.0.0"), "unsupported"),
        (lambda mapping: mapping.update(source_revision="short"), "full Git commit"),
        (lambda mapping: mapping.update(mappings=[]), "non-empty array"),
        (lambda mapping: mapping.update(mappings=["invalid"]), "must be an object"),
        (
            lambda mapping: mapping["mappings"][0].update(native_field=""),
            "native_field must be",
        ),
        (
            lambda mapping: mapping["mappings"][1].update(
                native_field=mapping["mappings"][0]["native_field"]
            ),
            "duplicate native_field",
        ),
        (
            lambda mapping: mapping["mappings"][0].update(riopa_field=None),
            "requires riopa_field",
        ),
        (
            lambda mapping: mapping["mappings"][-1].update(riopa_field="snapshot.state"),
            "unmapped mapping must not",
        ),
        (
            lambda mapping: mapping["mappings"][-2].update(
                classification="extension-only", riopa_field=123
            ),
            "must be a string or null",
        ),
        (
            lambda mapping: mapping["mappings"][0].update(rationale=""),
            "requires rationale",
        ),
    ],
)
def test_mapping_contract_rejects_each_invalid_shape(mutate, message: str) -> None:
    mapping = load_json(MAPPING)
    mutate(mapping)
    with pytest.raises(ValueError, match=message):
        validate_mapping(mapping)


def test_extension_mapping_may_name_an_explicit_extension_namespace() -> None:
    mapping = load_json(MAPPING)
    extension = next(
        item for item in mapping["mappings"] if item["classification"] == "extension-only"
    )
    extension["riopa_field"] = "extensions.fyi_archive.mirror_api_url"
    validate_mapping(mapping)
