"""Validation for bounded, rights-aware Australian FOI sampling plans."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

AU_JURISDICTIONS = {"FEDERAL", "NSW", "ACT", "QLD", "VIC", "WA", "SA", "TAS", "NT"}
OUTCOME_CLASSES = {
    "access",
    "partial_access",
    "refusal",
    "transfer",
    "extension",
    "fees",
    "invalid",
    "information_not_held",
    "review",
    "unknown",
}


def validate_sampling_frame(document: dict[str, Any]) -> dict[str, Any]:
    """Validate an AU sampling frame without authorizing live capture."""
    errors: list[str] = []
    if document.get("schema") != "fyi-archive.au-sampling-frame.v1":
        errors.append("unsupported sampling-frame schema")
    capture_authorized = document.get("capture_authorized")
    if capture_authorized is not True:
        errors.append("capture_authorized requires named human approval")
    if document.get("publication_authorized") is not False:
        errors.append("publication_authorized must remain false until named human approval")

    strata = document.get("strata")
    if not isinstance(strata, list) or not strata:
        errors.append("strata must be a non-empty array")
        strata = []
    seen: set[str] = set()
    for index, stratum in enumerate(strata):
        if not isinstance(stratum, dict):
            errors.append(f"strata[{index}] must be an object")
            continue
        jurisdiction = stratum.get("jurisdiction")
        if jurisdiction not in AU_JURISDICTIONS:
            errors.append(f"strata[{index}] has unknown jurisdiction")
        elif jurisdiction in seen:
            errors.append(f"duplicate jurisdiction stratum: {jurisdiction}")
        else:
            seen.add(str(jurisdiction))
        outcomes = stratum.get("outcomes")
        if not isinstance(outcomes, list) or not outcomes:
            errors.append(f"strata[{index}].outcomes must be non-empty")
        elif unknown := sorted(set(outcomes) - OUTCOME_CLASSES):
            errors.append(f"strata[{index}] has unknown outcomes: {unknown}")
        cap = stratum.get("request_cap")
        if not isinstance(cap, int) or cap < 1:
            errors.append(f"strata[{index}].request_cap must be a positive integer")

    if not {"FEDERAL", "NSW"}.issubset(seen):
        errors.append("initial pilot must include separate FEDERAL and NSW strata")

    if capture_authorized is True:
        authorization = document.get("operator_authorization")
        if not isinstance(authorization, dict) or not all(
            isinstance(authorization.get(field), str) and authorization[field]
            for field in ("authorized_by", "authorized_at", "scope")
        ):
            errors.append("capture_authorized requires a complete operator_authorization")

    rights = document.get("rights_gates")
    required_rights = {
        "source_terms_recorded",
        "takedown_route_recorded",
        "sensitive_data_review_required",
        "permitted_use_recorded",
    }
    if not isinstance(rights, dict):
        errors.append("rights_gates must be an object")
    elif missing := sorted(name for name in required_rights if rights.get(name) is not True):
        errors.append(f"rights_gates are incomplete: {missing}")

    return {"ok": not errors, "errors": errors, "jurisdictions": sorted(seen)}


def load_sampling_frame(path: Path) -> dict[str, Any]:
    """Load and validate a sampling-frame JSON document."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("sampling frame must be a JSON object")
    result = validate_sampling_frame(document)
    if not result["ok"]:
        raise ValueError("; ".join(result["errors"]))
    return document
