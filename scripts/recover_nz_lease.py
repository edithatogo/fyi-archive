"""Recover one failed NZ lease in the serialized, retained-evidence workflow."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fyi_archive.backfill_state_codec import decode_state, state_body_from_state
from fyi_archive.nz_backfill_state import validate_state
from fyi_archive.nz_lease_recovery import REPOSITORY, recover_failed_lease, state_sha256


def github(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Use the runner's scoped token without persisting environment or API output."""
    command = ["gh", "api", f"repos/{REPOSITORY}/{path}"]
    if payload is not None:
        command += ["--method", "PATCH", "--input", "-"]
    result = subprocess.run(
        command,
        input=json.dumps(payload) if payload is not None else None,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def read_state(issue: int) -> tuple[str, dict[str, Any]]:
    """Read only an open issue carrying the canonical NZ state label."""
    record = github(f"issues/{issue}")
    if record["state"] != "open" or "nz-real-backfill-state" not in {
        label["name"] for label in record["labels"]
    }:
        raise ValueError("issue is not the open NZ controller state")
    return record["body"], validate_state(decode_state(record["body"]))


def read_owner(run_id: int) -> dict[str, Any]:
    """Retain only the run identity and terminal-state fields needed for recovery."""
    run = github(f"actions/runs/{run_id}")
    fields = {
        key: run[key] for key in ("id", "status", "conclusion", "run_attempt", "path", "head_sha")
    }
    return {**fields, "repository": run["repository"]["full_name"]}


def prepare(issue: int, output: Path) -> None:
    """Capture the exact lease and owner without mutating controller state."""
    _, state = read_state(issue)
    if len(state["leases"]) != 1:
        raise ValueError("exactly one active lease is required")
    owner = read_owner(state["leases"][0]["run_id"])
    observation = {
        "state_sha256": state_sha256(state),
        "observed_at": datetime.now(UTC).isoformat(),
        "owner": owner,
        "issue": issue,
    }
    output.write_text(json.dumps(observation, indent=2) + "\n", encoding="utf-8")


def apply(issue: int, proposal: Path, artifact_id: int, digest: str, output: Path) -> None:
    """Recheck state and artifact retention before the serialized issue update."""
    expected_ref = f"{REPOSITORY}/.github/workflows/nz_real_backfill_recover.yml@refs/heads/main"
    if os.environ.get("GITHUB_WORKFLOW_REF") != expected_ref:
        raise ValueError("apply is restricted to the main-branch serialized recovery workflow")
    run_id = int(os.environ["GITHUB_RUN_ID"])
    observation = json.loads(proposal.read_text(encoding="utf-8"))
    if observation["issue"] != issue:
        raise ValueError("proposal issue does not match")
    body, state = read_state(issue)
    if len(state["leases"]) != 1:
        raise ValueError("exactly one active lease is required")
    observation["confirmed_owner"] = read_owner(observation["owner"]["id"])
    artifact = github(f"actions/artifacts/{artifact_id}")
    expected_digest = digest if digest.startswith("sha256:") else f"sha256:{digest}"
    if (
        artifact.get("expired") is not False
        or artifact.get("digest") != expected_digest
        or artifact.get("workflow_run", {}).get("id") != run_id
        or artifact.get("name") != f"nz-lease-recovery-{run_id}"
    ):
        raise ValueError("retained recovery artifact identity or digest does not match")
    lease = state["leases"][0]
    receipt = {
        "start_offset": lease["start_offset"],
        "batch_size": lease["end_offset"] - lease["start_offset"],
        "workflow_conclusion": "failure",
        "recovery_run_id": run_id,
        "artifact_url": f"https://github.com/{REPOSITORY}/actions/runs/{run_id}/artifacts/{artifact_id}",
        "artifact_digest": expected_digest,
    }
    updated = recover_failed_lease(
        state, observation=observation, receipt=receipt, now=datetime.now(UTC)
    )
    confirmed_body, _ = read_state(issue)
    if confirmed_body != body:
        raise ValueError("controller body changed before update")
    github(f"issues/{issue}", {"body": state_body_from_state(updated)})
    _, readback = read_state(issue)
    if state_sha256(readback) != state_sha256(updated):
        raise ValueError("controller readback differs; inspect before any retry")
    output.write_text(
        json.dumps(
            {
                "issue": issue,
                "state_sha256": state_sha256(updated),
                "recovered_run_id": observation["owner"]["id"],
                "completed_coverage_unchanged": True,
            },
            indent=2,
        )
        + "\n"
    )


def main() -> None:
    """Prepare by default; allow application only after workflow artifact retention."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "apply"))
    parser.add_argument("--issue", type=int, default=365)
    parser.add_argument("--proposal", type=Path, default=Path("recovery-observation.json"))
    parser.add_argument("--artifact-id", type=int)
    parser.add_argument("--artifact-digest")
    parser.add_argument("--output", type=Path, default=Path("recovery-result.json"))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.issue, args.proposal)
    elif args.artifact_id is None or args.artifact_digest is None:
        parser.error("apply requires retained artifact identity and digest")
    else:
        apply(args.issue, args.proposal, args.artifact_id, args.artifact_digest, args.output)


if __name__ == "__main__":
    main()
