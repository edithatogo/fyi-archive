"""Recovery must preserve completed work and refuse stale ownership evidence."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import pytest

from fyi_archive.nz_backfill_state import new_state, reserve_range
from fyi_archive.nz_lease_recovery import recover_failed_lease, state_sha256

NOW = datetime(2026, 8, 30, 9, 0, tzinfo=UTC)


def candidate():
    state = reserve_range(
        new_state(queue_count=100, completed=[{"start_offset": 0, "end_offset": 25}]),
        start_offset=25,
        batch_size=25,
        run_id=9,
    )
    owner = {
        "id": 9,
        "status": "completed",
        "conclusion": "failure",
        "run_attempt": 1,
        "repository": "edithatogo/fyi-archive",
        "path": ".github/workflows/nz_real_backfill_batch.yml",
        "head_sha": "a" * 40,
    }
    observation = {
        "state_sha256": state_sha256(state),
        "observed_at": NOW.isoformat(),
        "owner": owner,
        "confirmed_owner": deepcopy(owner),
    }
    receipt = {
        "start_offset": 25,
        "batch_size": 25,
        "workflow_conclusion": "failure",
        "recovery_run_id": 10,
        "artifact_url": "https://github.com/edithatogo/fyi-archive/actions/runs/10/artifacts/11",
        "artifact_digest": "sha256:" + "b" * 64,
    }
    return state, observation, receipt


def test_failed_exact_owner_requeues_without_crediting_work():
    state, observation, receipt = candidate()
    original = deepcopy(state)
    result = recover_failed_lease(state, observation=observation, receipt=receipt, now=NOW)
    assert state == original
    assert result["completed"] == original["completed"]
    assert result["receipts"] == original["receipts"]
    assert result["leases"] == []
    assert result["failures"][0]["recovery_observation"] == observation


@pytest.mark.parametrize(
    ("status", "conclusion"),
    [("in_progress", None), ("queued", None), ("completed", "success"), ("completed", None)],
)
def test_live_or_successful_owner_is_never_released(status, conclusion):
    state, observation, receipt = candidate()
    for key in ("owner", "confirmed_owner"):
        observation[key].update(status=status, conclusion=conclusion)
    with pytest.raises(ValueError, match="failed terminal"):
        recover_failed_lease(state, observation=observation, receipt=receipt, now=NOW)


@pytest.mark.parametrize(
    "mutation",
    [
        "state",
        "replacement",
        "attempt",
        "stale",
        "future",
        "repository",
        "workflow",
        "artifact",
        "digest",
        "invalid_attempt",
        "invalid_revision",
        "invalid_recovery_run",
    ],
)
def test_recovery_rejects_changed_or_unbound_evidence(mutation):
    state, observation, receipt = candidate()
    if mutation == "state":
        state["failures"].append({"other": "writer"})
    elif mutation == "replacement":
        state["leases"][0]["run_id"] = 12
        observation["state_sha256"] = state_sha256(state)
    elif mutation == "attempt":
        observation["confirmed_owner"]["run_attempt"] = 2
    elif mutation == "stale":
        observation["observed_at"] = "2026-08-29T09:00:00+00:00"
    elif mutation == "future":
        observation["observed_at"] = "2026-08-31T09:00:00+00:00"
    elif mutation in {"repository", "workflow"}:
        key = "repository" if mutation == "repository" else "path"
        for field in ("owner", "confirmed_owner"):
            observation[field][key] = "wrong"
    elif mutation == "artifact":
        receipt["artifact_url"] = receipt["artifact_url"].replace("runs/10", "runs/99")
    elif mutation in {"invalid_attempt", "invalid_revision"}:
        key = "run_attempt" if mutation == "invalid_attempt" else "head_sha"
        for field in ("owner", "confirmed_owner"):
            observation[field][key] = 0 if mutation == "invalid_attempt" else "bad"
    elif mutation == "invalid_recovery_run":
        receipt["recovery_run_id"] = 0
    else:
        receipt["artifact_digest"] = "sha256:abc"
    with pytest.raises(ValueError, match=r"state|owner|observation|artifact"):
        recover_failed_lease(state, observation=observation, receipt=receipt, now=NOW)
