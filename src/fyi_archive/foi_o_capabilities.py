"""Dependency-free validation of the published FOI-O capability contract."""

from __future__ import annotations

from typing import Any

SUPPORTED_CONTRACT_VERSIONS = {
    "foi-o-nz.core-event": {"foi-o-nz.core-event.v0.1.0"},
    "foi-o-nz.request-profile": {"foi-o-nz.request-profile.v0.1.0"},
}
CAPABILITY_SCHEMA_VERSION = "foi-o-nz.capability-declaration.v0.1.0"


def validate_foi_o_capabilities(document: dict[str, Any]) -> dict[str, Any]:
    """Validate a capability declaration and fail closed on unknown versions."""
    errors: list[str] = []
    if document.get("schema_version") != CAPABILITY_SCHEMA_VERSION:
        errors.append("unsupported capability declaration schema version")
    if not isinstance(document.get("consumer_id"), str) or not document["consumer_id"]:
        errors.append("consumer_id must be a non-empty string")
    capabilities = document.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        errors.append("capabilities must be a non-empty list")
        capabilities = []
    for index, capability in enumerate(capabilities):
        if not isinstance(capability, dict):
            errors.append(f"capabilities[{index}] must be an object")
            continue
        contract_id = capability.get("contract_id")
        versions = capability.get("supported_versions")
        if contract_id not in SUPPORTED_CONTRACT_VERSIONS:
            errors.append(f"capabilities[{index}] declares unsupported contract {contract_id!r}")
            continue
        if not isinstance(versions, list) or not versions:
            errors.append(f"capabilities[{index}].supported_versions must be non-empty")
            continue
        unknown = set(versions) - SUPPORTED_CONTRACT_VERSIONS[contract_id]
        if unknown:
            errors.append(f"capabilities[{index}] declares unknown versions: {sorted(unknown)}")
        if capability.get("unknown_version_behavior", "reject") != "reject":
            errors.append("fyi-archive requires reject as the unknown-version behavior")
    return {"ok": not errors, "errors": errors, "consumer_id": document.get("consumer_id")}
