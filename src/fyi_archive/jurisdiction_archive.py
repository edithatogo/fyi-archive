"""Evidence-led registry for incremental jurisdiction archive completion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ALLOWED_STATUSES = {"archived", "blocked", "unsupported"}
REQUIRED_EVIDENCE_FIELDS = {
    "source_issue",
    "capture_adapter",
    "rights_status",
    "manifest_status",
    "replay_status",
    "privacy_status",
}


def validate_target_registry(document: dict[str, Any]) -> dict[str, Any]:
    """Require an explicit, evidence-bearing status for every archive target."""
    errors: list[str] = []
    if document.get("schema") != "fyi-archive.jurisdiction-targets.v1":
        errors.append("unsupported jurisdiction-target registry schema")
    if document.get("publication_allowed") is not False:
        errors.append("publication_allowed must remain false")
    evidence_defaults = document.get("evidence_defaults")
    if not isinstance(evidence_defaults, dict):
        errors.append("evidence_defaults must be an object")
        evidence_defaults = {}
    targets = document.get("targets")
    if not isinstance(targets, list) or not targets:
        errors.append("targets must be a non-empty array")
        targets = []
    seen: set[str] = set()
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            errors.append(f"targets[{index}] must be an object")
            continue
        target_id = target.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            errors.append(f"targets[{index}] requires target_id")
        elif target_id in seen:
            errors.append(f"duplicate target_id: {target_id}")
        else:
            seen.add(target_id)
        if target.get("status") not in ALLOWED_STATUSES:
            errors.append(f"{target_id or index} requires archived, blocked, or unsupported status")
        evidence = target.get("evidence")
        if not isinstance(evidence, dict):
            errors.append(f"{target_id or index} requires evidence")
            continue
        effective_evidence = {**evidence_defaults, **evidence}
        missing = sorted(REQUIRED_EVIDENCE_FIELDS - effective_evidence.keys())
        if missing:
            errors.append(f"{target_id or index} evidence missing: {missing}")
        if target.get("status") == "archived":
            if not effective_evidence.get("manifest_sha256") or not effective_evidence.get(
                "capture_revision"
            ):
                errors.append(f"{target_id} archived status requires immutable manifest evidence")
        elif not target.get("blocker"):
            errors.append(f"{target_id or index} requires an explicit blocker")
    return {"ok": not errors, "errors": errors, "target_count": len(targets)}


def load_target_registry(path: Path) -> dict[str, Any]:
    """Load and validate a jurisdiction target registry."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("jurisdiction target registry must be a JSON object")
    result = validate_target_registry(document)
    if not result["ok"]:
        raise ValueError("; ".join(result["errors"]))
    return document
