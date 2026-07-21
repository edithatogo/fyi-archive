"""Validation for separately versioned FOI-O-derived archive outputs."""

from __future__ import annotations

import re
from typing import Any

HEX64 = re.compile(r"^[0-9a-f]{64}$")
CONTRACT = "foi-o-extraction-contract/0.1.0"
REQUIRED_PROVENANCE = {
    "source_repository",
    "source_revision",
    "source_digest",
    "extraction_run_id",
    "pipeline_id",
    "pipeline_version",
    "generated_at",
}


def validate_derived_manifest(document: dict[str, Any]) -> dict[str, Any]:
    """Validate a candidate derived-layer declaration and return diagnostics."""
    errors: list[str] = []
    if document.get("conforms_to") != CONTRACT:
        errors.append(f"conforms_to must be {CONTRACT}")
    if document.get("release_status") not in {"draft", "verified"}:
        errors.append("release_status must be draft or verified")
    if document.get("candidate_status") != "candidate":
        errors.append("derived outputs must retain candidate_status=candidate")
    if not isinstance(document.get("version"), str) or not document["version"]:
        errors.append("version must be a non-empty string")

    for name in ("ontology", "profile", "codebook"):
        value = document.get(name)
        if not isinstance(value, dict):
            errors.append(f"{name} must be an object")
            continue
        digest = value.get("sha256")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            errors.append(f"{name}.sha256 must be a lowercase SHA-256 digest")

    provenance = document.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("provenance must be an object")
    else:
        missing = sorted(REQUIRED_PROVENANCE - provenance.keys())
        errors.extend(f"provenance missing {field}" for field in missing)
        source_revision = provenance.get("source_revision")
        if source_revision in {"main", "latest", "HEAD"}:
            errors.append("provenance.source_revision must be immutable")
        source_digest = provenance.get("source_digest")
        if not isinstance(source_digest, str) or not HEX64.fullmatch(source_digest):
            errors.append("provenance.source_digest must be a lowercase SHA-256 digest")

    return {
        "ok": not errors,
        "errors": errors,
        "contract": document.get("conforms_to"),
        "version": document.get("version"),
        "release_status": document.get("release_status"),
    }
