"""Prepare exact failed-lease recovery; never infer successful capture from age."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

from fyi_archive.nz_backfill_state import abandon_range, validate_state

REPOSITORY = "edithatogo/fyi-archive"
WORKFLOW = ".github/workflows/nz_real_backfill_batch.yml"


def state_sha256(state: dict[str, Any]) -> str:
    """Bind a proposed transition to the complete normalized controller state."""
    data = json.dumps(validate_state(state), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()


def recover_failed_lease(
    state: dict[str, Any],
    *,
    observation: dict[str, Any],
    receipt: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    """Release only an exact failed owner with fresh, retained recovery evidence.

    The caller must fetch owner observations from GitHub, retain their diagnostic
    artifact, and serialize the final read and write with all controller writers.
    This pure transition is not a remote compare-and-swap operation.
    """
    checked = validate_state(state)
    if observation.get("state_sha256") != state_sha256(checked):
        raise ValueError("controller state changed since recovery observation")
    recorded = datetime.fromisoformat(observation["observed_at"])
    if (
        recorded.tzinfo is None
        or now.tzinfo is None
        or not 0 <= (now - recorded).total_seconds() <= 300
    ):
        raise ValueError("recovery observation is stale or future-dated")
    owner = observation["owner"]
    if owner != observation.get("confirmed_owner"):
        raise ValueError("owner changed while retaining recovery evidence")
    if owner.get("repository") != REPOSITORY or owner.get("path") != WORKFLOW:
        raise ValueError("recovery observation has the wrong repository or workflow")
    if owner.get("status") != "completed" or owner.get("conclusion") != "failure":
        raise ValueError("recovery requires a failed terminal owner")
    leases = checked["leases"]
    if len(leases) != 1 or leases[0].get("run_id") != owner.get("id"):
        raise ValueError("recovery observation does not match the exact active lease")
    if type(owner.get("run_attempt")) is not int or owner["run_attempt"] < 1:
        raise ValueError("owner attempt is invalid")
    if not re.fullmatch(r"[0-9a-f]{40}", str(owner.get("head_sha"))):
        raise ValueError("owner revision is invalid")
    _validate_retained_artifact(receipt)
    return abandon_range(
        checked,
        run_id=owner["id"],
        receipt={**receipt, "recovery_observation": observation},
    )


def _validate_retained_artifact(receipt: dict[str, Any]) -> None:
    run_id = receipt.get("recovery_run_id")
    if type(run_id) is not int or run_id < 1:
        raise ValueError("recovery artifact run is invalid")
    expected = rf"https://github\.com/{REPOSITORY}/actions/runs/{run_id}/artifacts/[1-9][0-9]*"
    if not re.fullmatch(expected, str(receipt.get("artifact_url"))):
        raise ValueError("recovery artifact must belong to the exact recovery run")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(receipt.get("artifact_digest"))):
        raise ValueError("recovery artifact requires a complete SHA-256 digest")
