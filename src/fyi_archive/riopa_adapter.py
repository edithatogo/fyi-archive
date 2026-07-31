"""Language-neutral, additive mapping of native fyi-archive evidence to RIOPA."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, cast

CLASSIFICATIONS = frozenset({"exact", "approximate", "extension-only", "unmapped"})


def canonical_sha256(value: object) -> str:
    """Return a stable digest for a language-neutral JSON value."""
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object, rejecting non-object roots."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def resolve_json_pointer(document: object, pointer: str) -> object:
    """Resolve an RFC 6901 JSON Pointer against a parsed JSON document."""
    if not pointer.startswith("/"):
        raise ValueError(f"invalid JSON Pointer: {pointer}")
    current = document
    for raw_token in pointer.removeprefix("/").split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            object_mapping = cast("dict[str, object]", current)
            if token not in object_mapping:
                raise ValueError(f"JSON Pointer token not found: {token}")
            current = object_mapping[token]
        elif isinstance(current, list):
            try:
                current = cast("list[object]", current)[int(token)]
            except (IndexError, ValueError) as error:
                raise ValueError(f"invalid JSON Pointer array index: {token}") from error
        else:
            raise ValueError(f"JSON Pointer traverses scalar at: {token}")
    return current


def validate_mapping(mapping: dict[str, Any]) -> None:
    """Validate the portable mapping contract used by central conformance."""
    required = {"schema_version", "repository", "source_revision", "profile_version", "mappings"}
    missing = required - mapping.keys()
    if missing:
        raise ValueError(f"mapping is missing required fields: {sorted(missing)}")
    if mapping["schema_version"] != "1.0.0":
        raise ValueError("unsupported mapping schema_version")
    source_revision = mapping["source_revision"]
    if not isinstance(source_revision, str) or len(source_revision) != 40:
        raise ValueError("source_revision must be a full Git commit")
    mappings = mapping["mappings"]
    if not isinstance(mappings, list) or not mappings:
        raise ValueError("mappings must be a non-empty array")
    seen: set[str] = set()
    for entry in mappings:
        if not isinstance(entry, dict):
            raise ValueError("every mapping must be an object")
        classification = entry.get("classification")
        if classification not in CLASSIFICATIONS:
            raise ValueError(f"invalid mapping classification: {classification}")
        native_field = entry.get("native_field")
        if not isinstance(native_field, str) or not native_field:
            raise ValueError("native_field must be a non-empty string")
        if native_field in seen:
            raise ValueError(f"duplicate native_field mapping: {native_field}")
        seen.add(native_field)
        riopa_field = entry.get("riopa_field")
        if classification in {"exact", "approximate"} and not isinstance(riopa_field, str):
            raise ValueError(f"{classification} mapping requires riopa_field")
        if classification in {"extension-only", "unmapped"} and riopa_field is not None:
            raise ValueError(f"{classification} mapping must not set riopa_field")
        for field in ("rationale", "evidence_fixture"):
            if not isinstance(entry.get(field), str) or not entry[field]:
                raise ValueError(f"mapping {native_field} requires {field}")


def build_adapter_report(
    mapping: dict[str, Any],
    fixture: dict[str, Any],
    *,
    fixture_filename: str = "native-evidence-fixture.json",
) -> dict[str, Any]:
    """Build a deterministic report while preserving the complete native fixture."""
    validate_mapping(mapping)
    projections = []
    for entry in mapping["mappings"]:
        filename, separator, pointer = entry["evidence_fixture"].partition("#")
        if separator != "#" or filename != fixture_filename:
            raise ValueError(f"unsupported evidence fixture reference: {entry['evidence_fixture']}")
        native_value = resolve_json_pointer(fixture, pointer)
        projections.append(
            {
                **copy.deepcopy(entry),
                "native_value": copy.deepcopy(native_value),
                "projected_value": (
                    copy.deepcopy(native_value)
                    if entry["classification"] in {"exact", "approximate"}
                    else None
                ),
            },
        )
    return {
        "schema_version": "1.0.0",
        "repository": mapping["repository"],
        "source_revision": mapping["source_revision"],
        "profile_version": mapping["profile_version"],
        "mapping_sha256": canonical_sha256(mapping),
        "fixture_sha256": canonical_sha256(fixture),
        "classifications_present": sorted({item["classification"] for item in projections}),
        "projections": projections,
        "native_evidence_fixture": copy.deepcopy(fixture),
        "limitations": copy.deepcopy(mapping.get("limitations", [])),
    }


def write_adapter_report(*, mapping_path: Path, fixture_path: Path, output_path: Path) -> None:
    """Build and write a canonical, deterministic adapter report."""
    report = build_adapter_report(
        load_json(mapping_path),
        load_json(fixture_path),
        fixture_filename=fixture_path.name,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
