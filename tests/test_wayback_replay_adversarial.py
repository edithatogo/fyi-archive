"""Adversarial tests for replay-state integrity and fail-closed boundaries."""

from __future__ import annotations

import json
import random
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fyi_archive.wayback_replay import (
    ReplayObservation,
    ReplayStateError,
    content_hash,
    object_path,
    record_observation,
    replacement_candidate,
    store_object,
    verify_journal,
    verify_resume_state,
    write_initial_state,
)

ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "wayback_replay_configuration.json"
NOW = datetime(2026, 7, 31, tzinfo=UTC)


def configuration() -> dict:
    return json.loads(FIXTURE.read_text())


def rewrite_checkpoint(root: Path, checkpoint: dict) -> None:
    value = dict(checkpoint)
    value.pop("checkpoint_sha256", None)
    value["checkpoint_sha256"] = content_hash(value)
    (root / "checkpoint.json").write_text(
        json.dumps(value, separators=(",", ":"), sort_keys=True) + "\n"
    )


def one_attempt(root: Path) -> tuple[dict, dict]:
    config = configuration()
    checkpoint = write_initial_state(root, config)
    checkpoint = record_observation(
        root=root,
        configuration=config,
        checkpoint=checkpoint,
        member_id="synthetic-001",
        occurrence_id="occurrence-1",
        attempt_number=1,
        observation=ReplayObservation(kind="success", response_bytes=b"synthetic"),
        now=NOW,
        rng=random.Random(1),
    )
    return config, checkpoint


def test_corrupt_existing_object_fails_closed(tmp_path: Path) -> None:
    digest = store_object(tmp_path, b"original")
    object_path(tmp_path, digest).write_bytes(b"corrupt")
    with pytest.raises(ReplayStateError, match="collision or corruption"):
        store_object(tmp_path, b"original")


def test_symlinked_object_fails_closed(tmp_path: Path) -> None:
    digest = store_object(tmp_path, b"original")
    path = object_path(tmp_path, digest)
    path.unlink()
    target = tmp_path / "outside"
    target.write_bytes(b"original")
    path.symlink_to(target)
    with pytest.raises(ReplayStateError, match="not a regular file"):
        store_object(tmp_path, b"original")


@pytest.mark.parametrize("digest", ["../escape", "A" * 64, "a" * 63, "absolute/path"])
def test_object_paths_reject_traversal_and_noncanonical_hashes(tmp_path: Path, digest: str) -> None:
    with pytest.raises(ReplayStateError, match="lowercase SHA-256"):
        object_path(tmp_path, digest)


@pytest.mark.parametrize(
    "field",
    [
        "selection_sha256",
        "replay_policy_sha256",
        "producer",
        "producer_version",
        "parser_version",
        "jitter_seed",
    ],
)
def test_resume_rejects_changed_configuration_binding(tmp_path: Path, field: str) -> None:
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    changed = json.loads(json.dumps(config))
    if field.endswith("sha256"):
        changed[field] = "f" * 64
    elif field == "jitter_seed":
        changed[field] += 1
    else:
        changed[field] += "-changed"
    with pytest.raises(ReplayStateError):
        verify_resume_state(tmp_path, changed, checkpoint)


def test_resume_rejects_reordered_members_even_with_rehashed_selection(tmp_path: Path) -> None:
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    changed = json.loads(json.dumps(config))
    changed["members"].reverse()
    changed["selection_sha256"] = content_hash(changed["members"])
    with pytest.raises(ReplayStateError, match="configuration"):
        verify_resume_state(tmp_path, changed, checkpoint)


def test_resume_rejects_tampered_persisted_configuration(tmp_path: Path) -> None:
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    path = tmp_path / "configuration.json"
    persisted = json.loads(path.read_text())
    persisted["producer_version"] = "tampered"
    path.write_text(json.dumps(persisted))
    with pytest.raises(ReplayStateError, match="persisted replay configuration"):
        verify_resume_state(tmp_path, config, checkpoint)


@pytest.mark.parametrize("mutation", ["delete", "insert", "mutate", "reorder"])
def test_journal_tampering_is_detected(tmp_path: Path, mutation: str) -> None:
    config, checkpoint = one_attempt(tmp_path)
    checkpoint = record_observation(
        root=tmp_path,
        configuration=config,
        checkpoint=checkpoint,
        member_id="synthetic-002",
        occurrence_id="occurrence-2",
        attempt_number=1,
        observation=ReplayObservation(kind="http", status_code=404),
        now=NOW,
        rng=random.Random(1),
    )
    path = tmp_path / "attempts.jsonl"
    lines = path.read_bytes().splitlines()
    if mutation == "delete":
        lines.pop(0)
    elif mutation == "insert":
        lines.insert(0, lines[0])
    elif mutation == "mutate":
        value = json.loads(lines[0])
        value["outcome_code"] = "tampered"
        lines[0] = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    else:
        lines.reverse()
    path.write_bytes(b"\n".join(lines) + b"\n")
    with pytest.raises(ReplayStateError):
        verify_resume_state(tmp_path, config, checkpoint)


def test_checkpoint_population_conservation_is_enforced(tmp_path: Path) -> None:
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    checkpoint["counts"]["pending"] = 1
    checkpoint.pop("checkpoint_sha256")
    checkpoint["checkpoint_sha256"] = content_hash(checkpoint)
    with pytest.raises(ReplayStateError, match="counts"):
        verify_resume_state(tmp_path, config, checkpoint)


def test_checkpoint_state_cannot_diverge_from_journal(tmp_path: Path) -> None:
    config, checkpoint = one_attempt(tmp_path)
    checkpoint["member_states"]["synthetic-001"] = "terminal"
    checkpoint["counts"]["complete"] = 0
    checkpoint["counts"]["terminal"] = 1
    checkpoint.pop("checkpoint_sha256")
    checkpoint["checkpoint_sha256"] = content_hash(checkpoint)
    with pytest.raises(ReplayStateError, match="attempt journal"):
        verify_resume_state(tmp_path, config, checkpoint)


@pytest.mark.parametrize(
    "observation",
    [
        ReplayObservation(kind="http", status_code=418),
        ReplayObservation(kind="transport", transport_code="tls_magic"),
        ReplayObservation(kind="terminal", terminal_code="unknown"),
        ReplayObservation(kind="success"),
    ],
)
def test_unknown_or_incomplete_observations_fail_closed(observation: ReplayObservation) -> None:
    from fyi_archive.wayback_replay import classify_observation

    with pytest.raises(ReplayStateError):
        classify_observation(observation)


@pytest.mark.parametrize(
    "url",
    [
        "https://other.test/request/synthetic-001.json",
        "https://example.test/request/other.json",
        "https://example.test/request/synthetic-001.json?changed=1",
        "https://example.test/request/synthetic-001.json#fragment",
        "https://user@example.test/request/synthetic-001.json",
        "https://example.test:444/request/synthetic-001.json",
    ],
)
def test_replacement_candidates_reject_any_url_change(url: str) -> None:
    with pytest.raises(ReplayStateError):
        replacement_candidate(
            member=configuration()["members"][0],
            candidate_url=url,
            capture_timestamp="2025-01-01T00:00:00Z",
            source_metadata_sha256="a" * 64,
            source_row_sha256="b" * 64,
        )


def test_candidate_cannot_activate_replay_membership(tmp_path: Path) -> None:
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    candidate = replacement_candidate(
        member=config["members"][0],
        candidate_url=config["members"][0]["canonical_url"],
        capture_timestamp="2025-01-01T00:00:00Z",
        source_metadata_sha256="a" * 64,
        source_row_sha256="b" * 64,
    )
    assert candidate["status"] == "pending_replay_approval"
    assert checkpoint["counts"]["population"] == 2
    assert list(checkpoint["member_states"]) == ["synthetic-001", "synthetic-002"]


def test_open_circuit_rejects_premature_transport_observation(tmp_path: Path) -> None:
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    for attempt in range(1, 4):
        checkpoint = record_observation(
            root=tmp_path,
            configuration=config,
            checkpoint=checkpoint,
            member_id="synthetic-001",
            occurrence_id=f"failure-{attempt}",
            attempt_number=attempt,
            observation=ReplayObservation(kind="http", status_code=503),
            now=NOW,
            rng=random.Random(1),
        )
    with pytest.raises(ReplayStateError, match="circuit is open"):
        record_observation(
            root=tmp_path,
            configuration=config,
            checkpoint=checkpoint,
            member_id="synthetic-001",
            occurrence_id="premature",
            attempt_number=4,
            observation=ReplayObservation(kind="http", status_code=503),
            now=NOW,
            rng=random.Random(1),
        )


def test_duplicate_occurrence_and_nonincreasing_attempt_are_rejected(tmp_path: Path) -> None:
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    checkpoint = record_observation(
        root=tmp_path,
        configuration=config,
        checkpoint=checkpoint,
        member_id="synthetic-001",
        occurrence_id="same",
        attempt_number=1,
        observation=ReplayObservation(kind="http", status_code=503),
        now=NOW,
        rng=random.Random(1),
    )
    with pytest.raises(ReplayStateError, match="occurrence"):
        record_observation(
            root=tmp_path,
            configuration=config,
            checkpoint=checkpoint,
            member_id="synthetic-001",
            occurrence_id="same",
            attempt_number=2,
            observation=ReplayObservation(kind="http", status_code=503),
            now=NOW,
            rng=random.Random(1),
        )
    with pytest.raises(ReplayStateError, match="increase"):
        record_observation(
            root=tmp_path,
            configuration=config,
            checkpoint=checkpoint,
            member_id="synthetic-001",
            occurrence_id="different",
            attempt_number=1,
            observation=ReplayObservation(kind="http", status_code=503),
            now=NOW,
            rng=random.Random(1),
        )


def test_independent_verifier_rejects_checkpoint_journal_mismatch(tmp_path: Path) -> None:
    _config, checkpoint = one_attempt(tmp_path)
    checkpoint["journal_entry_count"] = 0
    checkpoint["journal_tail_sha256"] = None
    rewrite_checkpoint(tmp_path, checkpoint)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_wayback_replay_state.py"), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "journal" in result.stderr


def test_resume_rejects_corrupt_referenced_object(tmp_path: Path) -> None:
    config, checkpoint = one_attempt(tmp_path)
    _, _, entries = verify_journal(tmp_path / "attempts.jsonl")
    object_path(tmp_path, entries[0]["object_sha256"]).write_bytes(b"tampered")
    with pytest.raises(ReplayStateError, match="integrity"):
        verify_resume_state(tmp_path, config, checkpoint)


def test_state_root_symlink_is_rejected(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(ReplayStateError, match="symlink"):
        write_initial_state(link, configuration())


def test_producer_contains_no_network_client() -> None:
    source = (ROOT / "src" / "fyi_archive" / "wayback_replay.py").read_text()
    assert "import httpx" not in source
    assert "import requests" not in source
    assert "urlopen" not in source
    assert "ObservationTransport" in source
