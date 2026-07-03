"""Shared helpers for automated FYI backfill state management."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any


def iso_now() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(UTC).isoformat()


def state_next_id(state: dict[str, Any] | None, fallback: int) -> int:
    """Return the verified next request ID from controller state."""
    if not state:
        return fallback
    raw_value = state.get("next_id", fallback)
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        msg = f"state next_id must be an integer, got {raw_value!r}"
        raise ValueError(msg) from exc


def state_batches(state: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return the controller's recorded batch list."""
    if not state:
        return []
    batches = state.get("batches") or []
    if not isinstance(batches, list):
        msg = "state batches must be a list"
        raise ValueError(msg)
    normalized: list[dict[str, Any]] = []
    for batch in batches:
        if isinstance(batch, dict):
            normalized.append(batch)
    return normalized


def has_pending_batches(state: dict[str, Any] | None) -> bool:
    """Return true when any dispatched batch is still pending verification."""
    return any(str(batch.get("status") or "pending") != "merged" for batch in state_batches(state))


def state_dispatch_next_id(state: dict[str, Any] | None, fallback: int) -> int:
    """Return the next request ID after the highest dispatched batch."""
    if not state:
        return fallback
    batches = state_batches(state)
    verified_next = state_next_id(state, fallback)
    if not batches:
        return verified_next
    highest_end = max(int(batch["id_to"]) for batch in batches)
    return max(verified_next, highest_end + 1, fallback)


def _batch_key(batch: dict[str, Any]) -> tuple[int, int, str]:
    return (int(batch["id_from"]), int(batch["id_to"]), str(batch.get("label") or ""))


def _normalize_batch(batch: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(batch)
    result["id_from"] = str(int(result["id_from"]))
    result["id_to"] = str(int(result["id_to"]))
    result["label"] = str(result.get("label") or f"{result['id_from']}-{result['id_to']}")
    result.setdefault("status", "pending")
    return result


def append_pending_batches(
    *,
    state: dict[str, Any],
    batches: list[dict[str, Any]],
    controller_run_id: str,
    controller_run_url: str,
) -> dict[str, Any]:
    """Append newly dispatched batches to controller state."""
    updated = deepcopy(state)
    existing = state_batches(updated)
    for batch in batches:
        normalized = _normalize_batch(batch)
        normalized["status"] = "pending"
        normalized["controller_run_id"] = controller_run_id
        normalized["controller_run_url"] = controller_run_url
        normalized["dispatched_at"] = iso_now()
        existing.append(normalized)
    existing.sort(key=_batch_key)
    updated["batches"] = existing
    updated.setdefault("dispatched", [])
    updated["dispatched"] = list(updated["dispatched"])
    updated["complete"] = False
    updated["updated_at"] = iso_now()
    return updated


def mark_merged_batches(
    *,
    state: dict[str, Any],
    merged_labels: list[str],
    worker_run_id: str,
    worker_run_url: str,
    id_to: int,
    record_counts_by_label: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Mark batch labels as merged and advance the verified cursor."""
    updated = deepcopy(state)
    merged_set = {str(label) for label in merged_labels}
    batches = state_batches(updated)
    for batch in batches:
        if str(batch.get("label") or "") in merged_set:
            batch["status"] = "merged"
            batch["merged_at"] = iso_now()
            batch["worker_run_id"] = worker_run_id
            batch["worker_run_url"] = worker_run_url
            if record_counts_by_label is not None:
                label = str(batch.get("label") or "")
                if label in record_counts_by_label:
                    batch["record_count"] = int(record_counts_by_label[label])
    batches.sort(key=_batch_key)
    cursor = state_next_id(updated, 1)
    for batch in batches:
        start = int(batch["id_from"])
        end = int(batch["id_to"])
        status = str(batch.get("status") or "pending")
        if end < cursor:
            continue
        if start > cursor:
            break
        if status != "merged":
            break
        cursor = end + 1
    updated["batches"] = batches
    updated["next_id"] = cursor
    updated["complete"] = cursor > id_to and not has_pending_batches(updated)
    updated["updated_at"] = iso_now()
    return updated
