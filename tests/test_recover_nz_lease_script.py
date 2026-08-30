"""Exercise retained evidence and conflict guards around the GitHub issue writer."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from fyi_archive.backfill_state_codec import decode_state, state_body_from_state
from fyi_archive.nz_backfill_state import new_state, reserve_range


@pytest.fixture
def recovery(monkeypatch):
    spec = importlib.util.spec_from_file_location("recovery_script", "scripts/recover_nz_lease.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv(
        "GITHUB_WORKFLOW_REF",
        "edithatogo/fyi-archive/.github/workflows/nz_real_backfill_recover.yml@refs/heads/main",
    )
    monkeypatch.setenv("GITHUB_RUN_ID", "10")
    return module


def install_api(recovery, monkeypatch):
    state = reserve_range(
        new_state(queue_count=100, completed=[{"start_offset": 0, "end_offset": 25}]),
        start_offset=25,
        batch_size=25,
        run_id=9,
    )
    server: dict[str, Any] = {
        "body": state_body_from_state(state),
        "writes": [],
        "reads": 0,
        "conflict": False,
        "expired": False,
        "running": False,
    }

    def github(path, payload=None):
        if path == "issues/365":
            if payload is not None:
                server["writes"].append(payload)
                server["body"] = payload["body"]
            else:
                server["reads"] += 1
            body = server["body"]
            if server["conflict"] and server["reads"] == 3:
                edited = decode_state(body)
                edited["failures"].append({"reason": "concurrent update"})
                body = state_body_from_state(edited)
            return {"body": body, "state": "open", "labels": [{"name": "nz-real-backfill-state"}]}
        if path == "actions/runs/9":
            return {
                "id": 9,
                "status": "in_progress" if server["running"] else "completed",
                "conclusion": None if server["running"] else "failure",
                "run_attempt": 1,
                "path": ".github/workflows/nz_real_backfill_batch.yml",
                "head_sha": "a" * 40,
                "repository": {"full_name": "edithatogo/fyi-archive"},
            }
        assert path == "actions/artifacts/11"
        return {
            "expired": server["expired"],
            "digest": "sha256:" + "b" * 64,
            "workflow_run": {"id": 10},
            "name": "nz-lease-recovery-10",
        }

    monkeypatch.setattr(recovery, "github", github)
    return server, state


def test_preparation_is_read_only_and_verified_apply_preserves_coverage(
    recovery, monkeypatch, tmp_path
):
    server, original = install_api(recovery, monkeypatch)
    proposal = tmp_path / "proposal.json"
    result = tmp_path / "result.json"
    recovery.prepare(365, proposal)
    assert server["writes"] == []
    recovery.apply(365, proposal, 11, "b" * 64, result)
    assert len(server["writes"]) == 1
    updated = decode_state(server["body"])
    assert updated["completed"] == original["completed"]
    assert updated["leases"] == []
    assert len(updated["failures"]) == 1
    assert json.loads(result.read_text())["completed_coverage_unchanged"] is True


@pytest.mark.parametrize("failure", ["conflict", "expired", "running", "wrong_branch"])
def test_application_never_writes_after_a_failed_precondition(
    recovery, monkeypatch, tmp_path, failure
):
    server, _ = install_api(recovery, monkeypatch)
    proposal = tmp_path / "proposal.json"
    recovery.prepare(365, proposal)
    if failure == "wrong_branch":
        monkeypatch.setenv("GITHUB_WORKFLOW_REF", "unapproved/branch")
    else:
        server[failure] = True
    with pytest.raises(ValueError, match=r"changed|artifact|owner|workflow"):
        recovery.apply(365, proposal, 11, "b" * 64, tmp_path / "result.json")
    assert server["writes"] == []


def test_recovery_serializes_with_capture_and_retains_evidence_before_apply():
    workflow = yaml.safe_load(Path(".github/workflows/nz_real_backfill_recover.yml").read_text())
    capture = yaml.safe_load(Path(".github/workflows/nz_real_backfill_batch.yml").read_text())
    assert workflow["concurrency"] == capture["concurrency"]
    steps = workflow["jobs"]["recover"]["steps"]
    retained = next(i for i, step in enumerate(steps) if step.get("id") == "evidence")
    apply = next(
        i for i, step in enumerate(steps) if "recover_nz_lease.py apply" in step.get("run", "")
    )
    assert retained < apply
    assert steps[retained]["with"]["if-no-files-found"] == "error"
    assert steps[apply]["if"] == "${{ inputs.dry_run == false }}"
