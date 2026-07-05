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


def _batch_requested_ids(batch: dict[str, Any]) -> int:
    return max(0, int(batch.get("id_to") or 0) - int(batch.get("id_from") or 0) + 1)


def _batch_cursor(batch: dict[str, Any]) -> int:
    return int(batch.get("id_to") or 0) + 1


def _sorted_batches(batches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(batches, key=_batch_key)


def _trim_history(entries: list[Any], limit: int) -> list[Any]:
    if limit < 1:
        return []
    if len(entries) <= limit:
        return list(entries)
    return list(entries[-limit:])


def _compute_summary_from_batches(
    state: dict[str, Any], *, dispatch_history_limit: int
) -> dict[str, Any]:
    batches = state_batches(state)
    pending_batches = [
        batch for batch in batches if str(batch.get("status") or "pending") != "merged"
    ]
    merged_batches = [
        batch for batch in batches if str(batch.get("status") or "pending") == "merged"
    ]
    dispatched_history = [
        entry for entry in state.get("dispatched") or [] if isinstance(entry, dict)
    ]
    worker_runs = sorted(
        {
            str(batch.get("worker_run_id"))
            for batch in merged_batches
            if str(batch.get("worker_run_id") or "")
        },
    )
    dispatched_requested_ids = sum(_batch_requested_ids(batch) for batch in batches)
    summary = {
        "dispatched_runs": len(dispatched_history),
        "dispatched_batches": len(batches),
        "dispatched_requested_ids": dispatched_requested_ids,
        "pending_batches": len(pending_batches),
        "merged_batches": len(merged_batches),
        "captured_records": sum(int(batch.get("record_count") or 0) for batch in merged_batches),
        "recent_worker_runs": _trim_history(worker_runs, dispatch_history_limit),
    }
    if dispatched_history:
        summary["recent_dispatch_runs"] = _trim_history(
            [
                str(entry.get("controller_run_id") or "")
                for entry in dispatched_history
                if str(entry.get("controller_run_id") or "")
            ],
            dispatch_history_limit,
        )
    return summary


def state_summary(state: dict[str, Any] | None) -> dict[str, Any]:
    """Return the controller summary, preferring compact state when present."""
    if not state:
        return {}
    summary = state.get("summary")
    if isinstance(summary, dict) and summary:
        return dict(summary)
    return _compute_summary_from_batches(state, dispatch_history_limit=10)


def prepare_backfill_state(
    state: dict[str, Any] | None,
    *,
    dispatch_history_limit: int = 10,
) -> dict[str, Any]:
    """Normalize and compact controller state for storage in GitHub issue bodies."""
    updated = deepcopy(state or {})
    batches = _sorted_batches(state_batches(updated))
    pending_batches = [
        batch for batch in batches if str(batch.get("status") or "pending") != "merged"
    ]
    summary = state_summary(updated)
    if not summary:
        summary = _compute_summary_from_batches(
            updated, dispatch_history_limit=dispatch_history_limit
        )
    else:
        summary = dict(summary)
        summary.setdefault("dispatched_runs", 0)
        summary.setdefault("dispatched_batches", 0)
        summary.setdefault("dispatched_requested_ids", 0)
        summary.setdefault("merged_batches", 0)
        summary.setdefault("captured_records", 0)
    summary["pending_batches"] = len(pending_batches)
    summary["last_updated_at"] = iso_now()

    dispatch_next_id = updated.get("dispatch_next_id")
    if dispatch_next_id is None and isinstance(summary, dict):
        dispatch_next_id = summary.get("dispatch_next_id")
    if dispatch_next_id is None:
        highest_dispatched_end = max((int(batch["id_to"]) for batch in batches), default=0)
        dispatch_next_id = max(state_next_id(updated, 1), highest_dispatched_end + 1)
    else:
        dispatch_next_id = int(dispatch_next_id)
    summary["dispatch_next_id"] = dispatch_next_id

    updated["batches"] = pending_batches
    if "dispatched" in updated and isinstance(updated["dispatched"], list):
        updated["dispatched"] = _trim_history(
            [entry for entry in updated["dispatched"] if isinstance(entry, dict)],
            dispatch_history_limit,
        )
    updated["summary"] = summary
    updated["dispatch_next_id"] = dispatch_next_id
    updated["complete"] = bool(state and state.get("complete"))
    if pending_batches:
        updated["complete"] = False
    updated["updated_at"] = iso_now()
    return updated


def has_pending_batches(state: dict[str, Any] | None) -> bool:
    """Return true when any dispatched batch is still pending verification."""
    return any(str(batch.get("status") or "pending") != "merged" for batch in state_batches(state))


def state_dispatch_next_id(state: dict[str, Any] | None, fallback: int) -> int:
    """Return the next request ID after the highest dispatched batch."""
    if not state:
        return fallback
    dispatch_next_id = state.get("dispatch_next_id")
    if dispatch_next_id is not None:
        try:
            return max(int(dispatch_next_id), fallback)
        except (TypeError, ValueError) as exc:
            msg = f"state dispatch_next_id must be an integer, got {dispatch_next_id!r}"
            raise ValueError(msg) from exc
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
    updated = prepare_backfill_state(state)
    existing = state_batches(updated)
    summary = dict(state_summary(updated))
    if not summary:
        summary = _compute_summary_from_batches(updated, dispatch_history_limit=10)
    for batch in batches:
        normalized = _normalize_batch(batch)
        normalized["status"] = "pending"
        normalized["controller_run_id"] = controller_run_id
        normalized["controller_run_url"] = controller_run_url
        normalized["dispatched_at"] = iso_now()
        existing.append(normalized)
        summary["dispatched_batches"] = int(summary.get("dispatched_batches") or 0) + 1
        summary["dispatched_requested_ids"] = int(
            summary.get("dispatched_requested_ids") or 0
        ) + _batch_requested_ids(normalized)
        summary["pending_batches"] = int(summary.get("pending_batches") or 0) + 1
        dispatch_next_id = max(int(updated.get("dispatch_next_id") or 1), _batch_cursor(normalized))
        updated["dispatch_next_id"] = dispatch_next_id
        summary["dispatch_next_id"] = dispatch_next_id
    summary["dispatched_runs"] = int(summary.get("dispatched_runs") or 0) + 1
    existing.sort(key=_batch_key)
    updated["batches"] = existing
    updated.setdefault("dispatched", [])
    updated["dispatched"] = list(updated["dispatched"])
    updated["summary"] = summary
    updated["complete"] = False
    updated["updated_at"] = iso_now()
    return prepare_backfill_state(updated)


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
    updated = prepare_backfill_state(state)
    merged_set = {str(label) for label in merged_labels}
    batches = state_batches(updated)
    summary = dict(state_summary(updated))
    if not summary:
        summary = _compute_summary_from_batches(updated, dispatch_history_limit=10)
    merged_count = 0
    merged_record_count = 0
    for batch in batches:
        if str(batch.get("label") or "") in merged_set:
            merged_count += 1
            batch["status"] = "merged"
            batch["merged_at"] = iso_now()
            batch["worker_run_id"] = worker_run_id
            batch["worker_run_url"] = worker_run_url
            if record_counts_by_label is not None:
                label = str(batch.get("label") or "")
                if label in record_counts_by_label:
                    batch["record_count"] = int(record_counts_by_label[label])
            merged_record_count += int(batch.get("record_count") or 0)
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
    pending_batches = [
        batch for batch in batches if str(batch.get("status") or "pending") != "merged"
    ]
    if not pending_batches:
        cursor = max(cursor, int(updated.get("dispatch_next_id") or 1))
    highest_pending_end = max((int(batch["id_to"]) for batch in pending_batches), default=0)
    dispatch_next_id = max(
        int(updated.get("dispatch_next_id") or 1), highest_pending_end + 1, cursor
    )
    summary["merged_batches"] = int(summary.get("merged_batches") or 0) + merged_count
    summary["captured_records"] = int(summary.get("captured_records") or 0) + merged_record_count
    summary["pending_batches"] = len(pending_batches)
    summary["dispatch_next_id"] = dispatch_next_id
    summary["last_updated_at"] = iso_now()
    if worker_run_id:
        recent_worker_runs = list(summary.get("recent_worker_runs") or [])
        if worker_run_id not in recent_worker_runs:
            recent_worker_runs.append(worker_run_id)
        summary["recent_worker_runs"] = _trim_history(recent_worker_runs, 10)
    updated["batches"] = pending_batches
    updated["next_id"] = cursor
    updated["dispatch_next_id"] = dispatch_next_id
    updated["summary"] = summary
    updated["complete"] = cursor > id_to and not has_pending_batches(updated)
    updated["updated_at"] = iso_now()
    return prepare_backfill_state(updated)
