"""Tests for durable NZ real-backfill range leasing."""

import pytest

from fyi_archive.nz_backfill_state import (
    complete_range,
    new_state,
    next_unclaimed_offset,
    reserve_range,
    validate_state,
)


def test_range_lease_rejects_completed_and_active_overlap() -> None:
    state = new_state(queue_count=1000, completed=[{"start_offset": 0, "end_offset": 500}])
    with pytest.raises(ValueError, match="overlaps"):
        reserve_range(state, start_offset=450, batch_size=100, run_id=1)

    leased = reserve_range(state, start_offset=500, batch_size=100, run_id=2)
    with pytest.raises(ValueError, match="overlaps"):
        reserve_range(leased, start_offset=550, batch_size=100, run_id=3)


def test_matching_run_can_idempotently_reassert_lease() -> None:
    state = reserve_range(new_state(queue_count=1000), start_offset=0, batch_size=100, run_id=7)
    assert reserve_range(state, start_offset=0, batch_size=100, run_id=7) == state


def test_completion_requires_receipt_matching_lease() -> None:
    state = reserve_range(new_state(queue_count=1000), start_offset=100, batch_size=100, run_id=8)
    with pytest.raises(ValueError, match="batch_size"):
        complete_range(state, run_id=8, receipt={"start_offset": 100, "batch_size": 99})

    completed = complete_range(
        state,
        run_id=8,
        receipt={"start_offset": 100, "batch_size": 100, "manifest_sha256": "a" * 64},
    )
    assert completed["leases"] == []
    assert completed["completed"] == [{"start_offset": 100, "end_offset": 200, "run_id": 8}]
    assert next_unclaimed_offset(completed) == 0


def test_next_offset_finds_first_gap_and_state_rejects_overlap() -> None:
    state = new_state(
        queue_count=1000,
        completed=[
            {"start_offset": 0, "end_offset": 500},
            {"start_offset": 600, "end_offset": 700},
        ],
    )
    assert next_unclaimed_offset(state) == 500
    with pytest.raises(ValueError, match="completed ranges overlap"):
        validate_state(
            {
                "schema": "fyi-archive.nz-real-backfill-state.v1",
                "queue_count": 1000,
                "completed": [
                    {"start_offset": 0, "end_offset": 100},
                    {"start_offset": 50, "end_offset": 150},
                ],
                "leases": [],
                "receipts": [],
            }
        )
