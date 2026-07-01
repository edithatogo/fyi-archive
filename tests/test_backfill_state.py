"""Tests for automated historical backfill state helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "backfill_state.py"
SPEC = importlib.util.spec_from_file_location("backfill_state", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load backfill_state.py")
backfill_state = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backfill_state)


def test_append_pending_batches_preserves_verified_cursor() -> None:
    state = {"next_id": 501, "batches": []}
    updated = backfill_state.append_pending_batches(
        state=state,
        batches=[{"id_from": "501", "id_to": "750", "label": "501-750"}],
        controller_run_id="123",
        controller_run_url="https://example.test/run/123",
    )

    assert updated["next_id"] == 501
    assert updated["complete"] is False
    assert updated["batches"][0]["status"] == "pending"
    assert backfill_state.has_pending_batches(updated) is True


def test_mark_merged_batches_advances_only_through_contiguous_merged_ranges() -> None:
    state = {
        "id_to": 1000,
        "next_id": 1,
        "batches": [
            {"id_from": "1", "id_to": "500", "label": "1-500", "status": "pending"},
            {"id_from": "501", "id_to": "1000", "label": "501-1000", "status": "pending"},
        ],
    }

    first = backfill_state.mark_merged_batches(
        state=state,
        merged_labels=["501-1000"],
        worker_run_id="run-2",
        worker_run_url="https://example.test/run/2",
        id_to=1000,
        record_counts_by_label={"501-1000": 2},
    )
    assert first["next_id"] == 1
    assert first["complete"] is False

    second = backfill_state.mark_merged_batches(
        state=first,
        merged_labels=["1-500"],
        worker_run_id="run-1",
        worker_run_url="https://example.test/run/1",
        id_to=1000,
        record_counts_by_label={"1-500": 3, "501-1000": 2},
    )
    assert second["next_id"] == 1001
    assert second["complete"] is True
    assert second["batches"][0]["record_count"] == 3
    assert backfill_state.has_pending_batches(second) is False
