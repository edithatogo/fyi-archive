"""Tests for durable NZ real-backfill range leasing."""

import pytest

from fyi_archive.nz_backfill_state import (
    abandon_range,
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
    assert completed["receipts"] == [
        {
            "start_offset": 100,
            "batch_size": 100,
            "manifest_sha256": "a" * 64,
            "run_id": 8,
            "end_offset": 200,
        }
    ]
    assert next_unclaimed_offset(completed) == 0


def test_abandon_requires_matching_failure_evidence_and_releases_lease() -> None:
    state = reserve_range(new_state(queue_count=1000), start_offset=600, batch_size=100, run_id=9)
    receipt = {
        "start_offset": 600,
        "batch_size": 100,
        "workflow_conclusion": "failure",
        "artifact_url": "https://github.example/actions/runs/9/artifacts/10",
        "artifact_digest": "sha256:abc",
    }
    abandoned = abandon_range(state, run_id=9, receipt=receipt)
    assert abandoned["leases"] == []
    assert abandoned["failures"] == [{**receipt, "run_id": 9, "end_offset": 700}]
    assert next_unclaimed_offset(abandoned) == 0


@pytest.mark.parametrize(
    ("receipt", "message"),
    [
        (
            {"start_offset": 601, "batch_size": 100, "workflow_conclusion": "failure"},
            "start_offset",
        ),
        (
            {"start_offset": 600, "batch_size": 99, "workflow_conclusion": "failure"},
            "batch_size",
        ),
        (
            {"start_offset": 600, "batch_size": 100, "workflow_conclusion": "success"},
            "workflow_conclusion",
        ),
        (
            {"start_offset": 600, "batch_size": 100, "workflow_conclusion": "failure"},
            "retained artifact",
        ),
    ],
)
def test_abandon_rejects_incomplete_or_mismatched_evidence(receipt, message) -> None:
    state = reserve_range(new_state(queue_count=1000), start_offset=600, batch_size=100, run_id=9)
    with pytest.raises(ValueError, match=message):
        abandon_range(state, run_id=9, receipt=receipt)


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


@pytest.mark.parametrize(
    ("state", "message"),
    [
        ({}, "unexpected NZ backfill state schema"),
        (
            {
                "schema": "fyi-archive.nz-real-backfill-state.v1",
                "queue_count": 0,
            },
            "queue_count must be positive",
        ),
        (
            {
                "schema": "fyi-archive.nz-real-backfill-state.v1",
                "queue_count": 100,
                "completed": [],
                "leases": [
                    {"start_offset": 0, "end_offset": 10, "run_id": 1},
                    {"start_offset": 10, "end_offset": 20, "run_id": 2},
                ],
            },
            "only one active NZ backfill lease",
        ),
        (
            {
                "schema": "fyi-archive.nz-real-backfill-state.v1",
                "queue_count": 100,
                "completed": [{"start_offset": -1, "end_offset": 10}],
            },
            "invalid NZ backfill range",
        ),
    ],
)
def test_state_rejects_malformed_controller_documents(state, message) -> None:
    with pytest.raises(ValueError, match=message):
        validate_state(state)


def test_state_rejects_invalid_reservations_and_completion_receipts() -> None:
    with pytest.raises(ValueError, match="queue_count must be positive"):
        new_state(queue_count=0)

    state = new_state(queue_count=100)
    with pytest.raises(ValueError, match="valid positive bounds"):
        reserve_range(state, start_offset=-1, batch_size=10, run_id=1)
    with pytest.raises(ValueError, match="exceeds"):
        reserve_range(state, start_offset=90, batch_size=11, run_id=1)
    with pytest.raises(ValueError, match="matching active lease"):
        complete_range(state, run_id=1, receipt={"start_offset": 0, "batch_size": 10})

    leased = reserve_range(state, start_offset=0, batch_size=10, run_id=1)
    with pytest.raises(ValueError, match="start_offset"):
        complete_range(leased, run_id=1, receipt={"start_offset": 1, "batch_size": 10})


def test_next_offset_advances_past_contiguous_completion() -> None:
    state = new_state(queue_count=100, completed=[{"start_offset": 0, "end_offset": 100}])
    assert next_unclaimed_offset(state) == 100
