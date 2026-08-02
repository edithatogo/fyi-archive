"""Externally pinned approval boundary for Wayback CDX evidence pairs."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PACKAGE_ROOT = Path(__file__).parent
SCHEMA_DIRECTORY = (
    PACKAGE_ROOT / "schemas"
    if (PACKAGE_ROOT / "schemas").is_dir()
    else PACKAGE_ROOT.parents[1] / "schemas"
)
APPROVAL_REGISTRY_PATH = PACKAGE_ROOT / "data" / "wayback_cdx_approval_registry.json"
APPROVED_APPROVAL_REGISTRY_SHA256 = (
    "ea8042d6c27c8fd73b0d1f1a95491c0ffc0cbf1ed9fb2701a9d538ee022fc8eb"
)
PROVENANCE_FIELDS = ("endpoint", "query_scope", "producer_id", "retrieved_at")


class CdxApprovalError(ValueError):
    """Raised when CDX evidence lacks an externally registered approval."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _strict_json(raw: bytes, label: str) -> object:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise CdxApprovalError(f"{label} contains duplicate key {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise CdxApprovalError(f"{label} contains non-finite number {value}")

    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=object_pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CdxApprovalError(f"{label} is not strict UTF-8 JSON") from error


def _validate_schema(filename: str, value: object) -> None:
    schema = _strict_json((SCHEMA_DIRECTORY / filename).read_bytes(), filename)
    try:
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
    except ValidationError as error:
        raise CdxApprovalError(f"{filename} validation failed: {error.message}") from error


def _require_digest(value: str, label: str) -> str:
    if not SHA256_RE.fullmatch(value):
        raise CdxApprovalError(f"{label} must be a lowercase SHA-256")
    return value


def _read_regular_file(path: Path, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise CdxApprovalError(f"{label} is missing or unsafe")
    try:
        return path.read_bytes()
    except OSError as error:
        raise CdxApprovalError(f"{label} is unreadable") from error


def registered_cdx_approval(artifact_sha256: str, retrieval_evidence_sha256: str) -> dict[str, Any]:
    """Resolve one exact evidence pair from the package-pinned approval registry."""
    artifact_digest = _require_digest(artifact_sha256, "CDX artifact SHA-256")
    evidence_digest = _require_digest(retrieval_evidence_sha256, "CDX retrieval-evidence SHA-256")
    registry_bytes = _read_regular_file(APPROVAL_REGISTRY_PATH, "approved CDX artifact registry")
    if _sha256_bytes(registry_bytes) != APPROVED_APPROVAL_REGISTRY_SHA256:
        raise CdxApprovalError("approved CDX artifact registry pin does not match")
    registry = cast(
        "dict[str, Any]",
        _strict_json(registry_bytes, "approved CDX artifact registry"),
    )
    _validate_schema("wayback-cdx-approval-registry.schema.json", registry)
    approvals = cast("list[dict[str, Any]]", registry["approvals"])
    approval_ids = [str(approval["approval_id"]) for approval in approvals]
    evidence_pairs = [
        (str(approval["artifact_sha256"]), str(approval["retrieval_evidence_sha256"]))
        for approval in approvals
    ]
    if len(set(approval_ids)) != len(approval_ids) or len(set(evidence_pairs)) != len(
        evidence_pairs
    ):
        raise CdxApprovalError("approved CDX artifact registry identities are not unique")
    matches = [
        approval
        for approval in approvals
        if approval["artifact_sha256"] == artifact_digest
        and approval["retrieval_evidence_sha256"] == evidence_digest
    ]
    if len(matches) != 1:
        raise CdxApprovalError(
            "evidence pair is absent or ambiguous in the approved CDX artifact registry"
        )
    return dict(matches[0])


def load_approved_cdx_evidence(
    *,
    artifact_path: Path,
    artifact_sha256: str,
    retrieval_evidence_path: Path,
    retrieval_evidence_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Load and cross-check one externally approved artifact and retrieval receipt."""
    approval = registered_cdx_approval(artifact_sha256, retrieval_evidence_sha256)
    artifact_bytes = _read_regular_file(artifact_path, "replacement CDX metadata artifact")
    evidence_bytes = _read_regular_file(
        retrieval_evidence_path, "replacement CDX retrieval evidence"
    )
    if _sha256_bytes(artifact_bytes) != approval["artifact_sha256"]:
        raise CdxApprovalError("replacement CDX metadata artifact hash does not match")
    if _sha256_bytes(evidence_bytes) != approval["retrieval_evidence_sha256"]:
        raise CdxApprovalError("replacement CDX retrieval-evidence hash does not match")
    artifact = cast(
        "dict[str, Any]",
        _strict_json(artifact_bytes, "replacement CDX metadata artifact"),
    )
    evidence = cast(
        "dict[str, Any]",
        _strict_json(evidence_bytes, "replacement CDX retrieval evidence"),
    )
    _validate_schema("wayback-cdx-metadata-artifact.schema.json", artifact)
    _validate_schema("wayback-cdx-retrieval-evidence.schema.json", evidence)
    if evidence["artifact_sha256"] != approval["artifact_sha256"]:
        raise CdxApprovalError("retrieval evidence does not bind the approved CDX artifact")
    for field in PROVENANCE_FIELDS:
        expected = approval[field]
        if artifact[field] != expected or evidence[field] != expected:
            raise CdxApprovalError(f"approved CDX provenance differs for {field}")
    return approval, artifact, evidence


def query_scope_allows_url(query_scope: str, canonical_url: str) -> bool:
    """Return whether one canonical URL is inside the exact registered query scope."""
    if query_scope.endswith("*"):
        return canonical_url.startswith(query_scope[:-1])
    return canonical_url == query_scope
