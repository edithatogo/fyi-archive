"""Durable range leasing for the NZ real-corpus backfill."""

from __future__ import annotations

from copy import deepcopy
from itertools import pairwise
from operator import itemgetter
from typing import Any

STATE_SCHEMA = "fyi-archive.nz-real-backfill-state.v1"


def new_state(*, queue_count: int, completed: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Create an empty controller state with optional reconciled ranges."""
    if queue_count < 1:
        raise ValueError("queue_count must be positive")
    state: dict[str, Any] = {
        "schema": STATE_SCHEMA,
        "queue_count": queue_count,
        "completed": completed or [],
        "leases": [],
        "receipts": [],
        "failures": [],
    }
    return validate_state(state)


def validate_state(state: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize controller state."""
    normalized = deepcopy(state)
    if normalized.get("schema") != STATE_SCHEMA:
        raise ValueError("unexpected NZ backfill state schema")
    queue_count = int(normalized.get("queue_count", 0))
    if queue_count < 1:
        raise ValueError("queue_count must be positive")
    normalized["queue_count"] = queue_count
    completed = [_normalize_range(item, queue_count) for item in normalized.get("completed", [])]
    completed.sort(key=itemgetter("start_offset", "end_offset"))
    _reject_overlaps(completed, "completed ranges overlap")
    leases = [_normalize_range(item, queue_count) for item in normalized.get("leases", [])]
    if len(leases) > 1:
        raise ValueError("only one active NZ backfill lease is allowed")
    _reject_cross_overlaps(completed, leases)
    normalized["completed"] = completed
    normalized["leases"] = leases
    normalized["receipts"] = list(normalized.get("receipts", []))
    normalized["failures"] = list(normalized.get("failures", []))
    return normalized


def reserve_range(
    state: dict[str, Any], *, start_offset: int, batch_size: int, run_id: int
) -> dict[str, Any]:
    """Reserve one range, rejecting completed or concurrently leased work."""
    updated = validate_state(state)
    requested = _requested_range(updated, start_offset, batch_size, run_id)
    for lease in updated["leases"]:
        if lease["run_id"] == run_id and _same_span(lease, requested):
            return updated
    _reject_cross_overlaps(updated["completed"], [requested])
    _reject_cross_overlaps(updated["leases"], [requested])
    if updated["leases"]:
        raise ValueError("only one active NZ backfill lease is allowed")
    updated["leases"].append(requested)
    return validate_state(updated)


def complete_range(
    state: dict[str, Any], *, run_id: int, receipt: dict[str, Any]
) -> dict[str, Any]:
    """Convert the matching lease into a durable completed range and receipt."""
    updated = validate_state(state)
    matches = [lease for lease in updated["leases"] if lease["run_id"] == run_id]
    if len(matches) != 1:
        raise ValueError("exactly one matching active lease is required")
    lease = matches[0]
    if int(receipt.get("start_offset", -1)) != lease["start_offset"]:
        raise ValueError("receipt start_offset does not match lease")
    if int(receipt.get("batch_size", -1)) != lease["end_offset"] - lease["start_offset"]:
        raise ValueError("receipt batch_size does not match lease")
    updated["leases"] = []
    updated["completed"].append(lease)
    updated["completed"].sort(key=itemgetter("start_offset", "end_offset"))
    stored_receipt = deepcopy(receipt)
    stored_receipt["run_id"] = run_id
    stored_receipt["end_offset"] = lease["end_offset"]
    updated["receipts"].append(stored_receipt)
    return validate_state(updated)


def abandon_range(state: dict[str, Any], *, run_id: int, receipt: dict[str, Any]) -> dict[str, Any]:
    """Release an exact failed lease while retaining its recovery evidence."""
    updated = validate_state(state)
    matches = [lease for lease in updated["leases"] if lease["run_id"] == run_id]
    if len(matches) != 1:
        raise ValueError("exactly one matching active lease is required")
    lease = matches[0]
    if int(receipt.get("start_offset", -1)) != lease["start_offset"]:
        raise ValueError("failure receipt start_offset does not match lease")
    if int(receipt.get("batch_size", -1)) != lease["end_offset"] - lease["start_offset"]:
        raise ValueError("failure receipt batch_size does not match lease")
    if receipt.get("workflow_conclusion") != "failure":
        raise ValueError("failure receipt must record workflow_conclusion=failure")
    if not receipt.get("artifact_url") or not receipt.get("artifact_digest"):
        raise ValueError("failure receipt must identify its retained artifact")
    updated["leases"] = []
    stored_receipt = deepcopy(receipt)
    stored_receipt["run_id"] = run_id
    stored_receipt["end_offset"] = lease["end_offset"]
    updated["failures"].append(stored_receipt)
    return validate_state(updated)


def next_unclaimed_offset(state: dict[str, Any]) -> int:
    """Return the first gap in completed ranges, including zero."""
    normalized = validate_state(state)
    cursor = 0
    for item in normalized["completed"]:
        if item["start_offset"] > cursor:
            return cursor
        cursor = max(cursor, item["end_offset"])
    return cursor


def next_dispatch_offset(state: dict[str, Any]) -> int:
    """Refuse dispatch while a lease exists, including an abandoned failed run."""
    normalized = validate_state(state)
    if normalized["leases"]:
        run_id = normalized["leases"][0].get("run_id")
        raise ValueError(
            f"active NZ backfill lease held by run {run_id}; retain recovery evidence before retry"
        )
    return next_unclaimed_offset(normalized)


def _requested_range(
    state: dict[str, Any], start_offset: int, batch_size: int, run_id: int
) -> dict[str, int]:
    if start_offset < 0 or batch_size < 1 or run_id < 1:
        raise ValueError("start_offset, batch_size, and run_id must be valid positive bounds")
    end_offset = start_offset + batch_size
    if end_offset > state["queue_count"]:
        raise ValueError("requested range exceeds the reconciled queue")
    return {"start_offset": start_offset, "end_offset": end_offset, "run_id": run_id}


def _normalize_range(item: dict[str, Any], queue_count: int) -> dict[str, Any]:
    normalized = deepcopy(item)
    start = int(normalized.get("start_offset", -1))
    end = int(normalized.get("end_offset", -1))
    if start < 0 or end <= start or end > queue_count:
        raise ValueError("invalid NZ backfill range")
    normalized["start_offset"] = start
    normalized["end_offset"] = end
    if "run_id" in normalized:
        normalized["run_id"] = int(normalized["run_id"])
    return normalized


def _same_span(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (left["start_offset"], left["end_offset"]) == (
        right["start_offset"],
        right["end_offset"],
    )


def _overlaps(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return left["start_offset"] < right["end_offset"] and right["start_offset"] < left["end_offset"]


def _reject_overlaps(ranges: list[dict[str, Any]], message: str) -> None:
    for previous, current in pairwise(ranges):
        if _overlaps(previous, current):
            raise ValueError(message)


def _reject_cross_overlaps(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> None:
    for existing in left:
        for requested in right:
            if _overlaps(existing, requested):
                raise ValueError("requested NZ backfill range overlaps existing state")
