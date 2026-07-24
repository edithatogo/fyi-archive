from __future__ import annotations

import json
from pathlib import Path

import pytest

from fyi_archive.jurisdiction_archive import load_target_registry, validate_target_registry

REGISTRY = Path("configs/jurisdiction_archive_targets.json")


def test_every_roadmap_target_has_explicit_evidence_status() -> None:
    document = load_target_registry(REGISTRY)
    targets = document["targets"]
    assert len(targets) == 42
    assert len({target["target_id"] for target in targets}) == 42
    assert {target["status"] for target in targets} <= {"archived", "blocked", "unsupported"}
    assert document["publication_allowed"] is False


def test_registry_rejects_silent_fallback_and_false_archive_claim() -> None:
    document = json.loads(REGISTRY.read_text(encoding="utf-8"))
    document["targets"][0]["status"] = "archived"
    document["targets"][0]["blocker"] = ""
    result = validate_target_registry(document)
    assert result["ok"] is False
    assert "immutable manifest evidence" in " ".join(result["errors"])

    document = json.loads(REGISTRY.read_text(encoding="utf-8"))
    document["targets"][0].pop("blocker")
    result = validate_target_registry(document)
    assert result["ok"] is False
    assert "explicit blocker" in " ".join(result["errors"])


def test_registry_reports_structural_evidence_errors(tmp_path: Path) -> None:
    result = validate_target_registry({
        "schema": "wrong",
        "publication_allowed": True,
        "evidence_defaults": None,
        "targets": [
            "not-an-object",
            {
                "target_id": "",
                "status": "pending",
                "evidence": None,
            },
            {
                "target_id": "DUP",
                "status": "blocked",
                "blocker": "missing",
                "evidence": {},
            },
            {
                "target_id": "DUP",
                "status": "blocked",
                "blocker": "missing",
                "evidence": {},
            },
        ],
    })
    errors = " ".join(result["errors"])
    assert result["ok"] is False
    assert "unsupported" in errors
    assert "publication_allowed" in errors
    assert "evidence_defaults" in errors
    assert "must be an object" in errors
    assert "requires target_id" in errors
    assert "requires archived" in errors
    assert "duplicate target_id" in errors
    assert "evidence missing" in errors

    path = tmp_path / "targets.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        load_target_registry(path)


def test_registry_requires_non_empty_targets() -> None:
    result = validate_target_registry({
        "schema": "fyi-archive.jurisdiction-targets.v1",
        "publication_allowed": False,
        "evidence_defaults": {},
        "targets": [],
    })
    assert result["ok"] is False
    assert "non-empty" in " ".join(result["errors"])
