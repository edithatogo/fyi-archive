"""Shared helpers for automated FYI backfill state management."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, cast


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
    batches = state.get("batches")
    if batches is None:
        return []
    if not isinstance(batches, list):
        msg = "state batches must be a list"
        raise ValueError(msg)
    return _dict_entries(cast("list[object]", batches))


def _dict_entries(value: object) -> list[dict[str, Any]]:
    """Return dictionary entries from an untrusted state value."""
    if not isinstance(value, list):
        return []
    entries = cast("list[object]", value)
    return [cast("dict[str, Any]", entry) for entry in entries if isinstance(entry, dict)]


def has_pending_batches(state: dict[str, Any] | None) -> bool:
    """Return true when any dispatched batch is still pending verification."""
    return any(str(batch.get("status") or "pending") != "merged" for batch in state_batches(state))


def pending_batches_for_requeue(
    state: dict[str, Any] | None, *, max_batches: int
) -> list[dict[str, Any]]:
    """Return a bounded, stable list of pending batches suitable for retry."""
    if max_batches < 1:
        msg = "max_batches must be positive"
        raise ValueError(msg)
    pending = [
        deepcopy(batch)
        for batch in state_batches(state)
        if str(batch.get("status") or "pending") == "pending"
    ]
    pending.sort(key=_batch_key)
    return pending[:max_batches]


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


def batch_span_from_label(label: str) -> tuple[int, int]:
    """Return the inclusive request-ID span represented by a batch label."""
    start_str, end_str = str(label).split("-", 1)
    return int(start_str), int(end_str)


def controller_labels_from_chunk_labels(chunk_labels: list[str]) -> list[str]:
    """Collapse worker chunk labels into the controller batch label."""
    spans = [batch_span_from_label(label) for label in chunk_labels]
    if not spans:
        return []
    starts = [start for start, _ in spans]
    ends = [end for _, end in spans]
    return [f"{min(starts)}-{max(ends)}"]


def _normalize_batch(batch: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(batch)
    result["id_from"] = str(int(result["id_from"]))
    result["id_to"] = str(int(result["id_to"]))
    result["label"] = str(result.get("label") or f"{result['id_from']}-{result['id_to']}")
    result.setdefault("status", "pending")
    return result


def refresh_summary(state: dict[str, Any], *, id_to: int | None = None) -> dict[str, Any]:
    """Recompute summary counters from the live controller state."""
    updated = deepcopy(state)
    batches = state_batches(updated)
    dispatched = _dict_entries(updated.get("dispatched"))
    pending_batches = [
        batch for batch in batches if str(batch.get("status") or "pending") == "pending"
    ]
    merged_batches = [batch for batch in batches if str(batch.get("status") or "") == "merged"]
    dispatched_requested_ids = sum(
        max(0, int(batch["id_to"]) - int(batch["id_from"]) + 1) for batch in batches
    )
    summary = dict(updated.get("summary") or {})
    summary.update(
        {
            "captured_records": sum(
                int(batch.get("record_count") or 0) for batch in merged_batches
            ),
            "dispatch_next_id": state_dispatch_next_id(updated, int(updated.get("id_from") or 1)),
            "dispatched_batches": len(batches),
            "dispatched_requested_ids": dispatched_requested_ids,
            "dispatched_runs": len(dispatched),
            "last_updated_at": iso_now(),
            "merged_batches": len(merged_batches),
            "pending_batches": len(pending_batches),
        },
    )
    if id_to is not None:
        summary["complete"] = state_next_id(updated, 1) > id_to and not has_pending_batches(updated)
    recent_dispatch_runs: list[str] = []
    for entry in dispatched[-10:]:
        run_id = entry.get("controller_run_id")
        if isinstance(run_id, str) and run_id:
            recent_dispatch_runs.append(run_id)
    if recent_dispatch_runs:
        summary["recent_dispatch_runs"] = recent_dispatch_runs
    recent_worker_runs: list[str] = []
    for batch in batches:
        run_id = batch.get("worker_run_id")
        if isinstance(run_id, str) and run_id and run_id not in recent_worker_runs:
            recent_worker_runs.append(run_id)
    if recent_worker_runs:
        summary["recent_worker_runs"] = recent_worker_runs[-10:]
    updated["summary"] = summary
    return updated


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
    updated = refresh_summary(updated)
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
    updated = refresh_summary(updated, id_to=id_to)
    updated["updated_at"] = iso_now()
    return updated
