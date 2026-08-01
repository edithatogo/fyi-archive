"""Adversarial tests for replay-state integrity and fail-closed boundaries."""

from __future__ import annotations

import json
import random
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import fyi_archive.wayback_cdx_approvals as approval_module
import fyi_archive.wayback_replay as replay_module
from fyi_archive.wayback_replay import (
    ReplayObservation,
    ReplayStateError,
    classify_observation,
    content_hash,
    merge_replacement_candidates,
    object_path,
    record_observation,
    replacement_candidate,
    sha256_bytes,
    store_object,
    validate_configuration,
    verify_journal,
    verify_resume_state,
    write_initial_state,
)

ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "wayback_replay_configuration.json"
APPROVED_CDX_METADATA = ROOT / "tests" / "fixtures" / "wayback-approved-cdx-metadata.json"
APPROVED_CDX_EVIDENCE = ROOT / "tests" / "fixtures" / "wayback-approved-cdx-retrieval-evidence.json"
NOW = datetime(2026, 7, 31, tzinfo=UTC)


def symlink_or_skip(link: Path, target: Path) -> None:
    """Create a symlink or skip where the platform policy forbids it."""
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except OSError as error:
        pytest.skip(f"symlink creation is unavailable: {error}")


def configuration() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text())


def repin_policy(config: dict[str, Any]) -> None:
    config["replay_policy_sha256"] = content_hash(config["policy"])


def approved_cdx_evidence() -> tuple[Path, str, str, Path, str]:
    artifact = json.loads(APPROVED_CDX_METADATA.read_text())
    return (
        APPROVED_CDX_METADATA,
        sha256_bytes(APPROVED_CDX_METADATA.read_bytes()),
        str(artifact["rows"][0]["row_sha256"]),
        APPROVED_CDX_EVIDENCE,
        sha256_bytes(APPROVED_CDX_EVIDENCE.read_bytes()),
    )


def write_cdx_metadata(
    root: Path,
    *,
    member_id: str = "synthetic-001",
    canonical_url: str = "https://example.test/request/synthetic-001.json",
    capture_timestamp: str = "2025-01-01T00:00:00Z",
) -> tuple[Path, str, str]:
    row: dict[str, object] = {
        "member_id": member_id,
        "canonical_url": canonical_url,
        "capture_timestamp": capture_timestamp,
        "archive_url": "https://web.archive.org/web/20250101000000id_/" + canonical_url,
        "status_code": 200,
        "digest": "sha256:synthetic-cdx-digest",
    }
    row["row_sha256"] = content_hash(row)
    artifact = {
        "schema": "fyi-archive.wayback-cdx-metadata-artifact.v1",
        "source": "Internet Archive CDX",
        "endpoint": "https://web.archive.org/cdx/search/cdx",
        "query_scope": canonical_url,
        "producer_id": "caller-controlled-producer",
        "retrieved_at": "2026-07-31T00:00:00Z",
        "rows": [row],
    }
    path = root / "cdx-metadata.json"
    path.write_text(
        json.dumps(
            artifact,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path, sha256_bytes(path.read_bytes()), str(row["row_sha256"])


def rewrite_checkpoint(root: Path, checkpoint: dict[str, Any]) -> None:
    value = dict(checkpoint)
    value.pop("checkpoint_sha256", None)
    value["checkpoint_sha256"] = content_hash(value)
    (root / "checkpoint.json").write_text(
        json.dumps(value, separators=(",", ":"), sort_keys=True) + "\n"
    )


def one_attempt(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config = configuration()
    checkpoint = write_initial_state(root, config)
    checkpoint = record_observation(
        root=root,
        configuration=config,
        checkpoint=checkpoint,
        member_id="synthetic-001",
        occurrence_id="occurrence-1",
        attempt_number=1,
        observation=ReplayObservation(
            kind="success",
            response_bytes=b"synthetic",
            final_url="https://web.archive.org/web/20260101000000id_/https://example.test/",
            content_type="application/json",
        ),
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
    symlink_or_skip(path, target)
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
        "boundary_registry_sha256",
        "boundary_profile_id",
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
    with pytest.raises(ReplayStateError):
        classify_observation(observation, policy=configuration()["policy"])


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("final_url", "https://righttoknow.example/request/1", "archive host"),
        ("final_url", "https://user@web.archive.org/web/1", "archive URL"),
        ("content_type", "application/octet-stream", "content type"),
        ("response_bytes", b"x" * 16_777_217, "payload"),
    ],
    ids=("foreign-host", "credentialed-url", "content-type", "oversized-payload"),
)
def test_success_boundary_fails_before_cas_persistence(
    tmp_path: Path, field: str, value: str | bytes, message: str
) -> None:
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    response_bytes = (
        value if field == "response_bytes" and isinstance(value, bytes) else b"synthetic"
    )
    final_url = (
        value
        if field == "final_url" and isinstance(value, str)
        else "https://web.archive.org/web/20260101000000id_/https://example.test/"
    )
    content_type = (
        value
        if field == "content_type" and isinstance(value, str)
        else "application/json; charset=utf-8"
    )
    with pytest.raises(ReplayStateError, match=message):
        record_observation(
            root=tmp_path,
            configuration=config,
            checkpoint=checkpoint,
            member_id="synthetic-001",
            occurrence_id="bad-observation",
            attempt_number=1,
            observation=ReplayObservation(
                kind="success",
                response_bytes=response_bytes,
                final_url=final_url,
                content_type=content_type,
            ),
            now=NOW,
            rng=random.Random(1),
        )
    assert not (tmp_path / "objects").exists()
    assert not (tmp_path / "attempts.jsonl").exists()


def test_rehashed_off_archive_attempt_fails_producer_and_independent_verifier(
    tmp_path: Path,
) -> None:
    config, checkpoint = one_attempt(tmp_path)
    journal_path = tmp_path / "attempts.jsonl"
    entry = json.loads(journal_path.read_text())
    entry["final_url"] = "https://live-origin.example/request/1"
    entry.pop("entry_sha256")
    entry["entry_sha256"] = content_hash(entry)
    journal_path.write_text(json.dumps(entry, separators=(",", ":"), sort_keys=True) + "\n")
    checkpoint["journal_tail_sha256"] = entry["entry_sha256"]
    rewrite_checkpoint(tmp_path, checkpoint)
    persisted_checkpoint = json.loads((tmp_path / "checkpoint.json").read_text())

    with pytest.raises(ReplayStateError, match="archive host"):
        verify_resume_state(tmp_path, config, persisted_checkpoint)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_wayback_replay_state.py"), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "archive host" in result.stderr


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("archive_hosts", ["righttoknow.example"]),
        ("allowed_content_types", ["application/octet-stream"]),
        ("max_payload_bytes", 2**40),
    ],
)
def test_resealed_policy_cannot_expand_external_replay_boundary(
    tmp_path: Path, field: str, value: object
) -> None:
    config = configuration()
    config["policy"][field] = value
    repin_policy(config)
    with pytest.raises(ReplayStateError, match="boundary registry"):
        validate_configuration(config)

    valid = configuration()
    checkpoint = write_initial_state(tmp_path, valid)
    persisted = json.loads((tmp_path / "configuration.json").read_text())
    persisted["policy"][field] = value
    repin_policy(persisted)
    (tmp_path / "configuration.json").write_text(json.dumps(persisted))
    checkpoint["replay_policy_sha256"] = persisted["replay_policy_sha256"]
    checkpoint["configuration_sha256"] = content_hash(persisted)
    checkpoint.pop("checkpoint_sha256")
    checkpoint["checkpoint_sha256"] = content_hash(checkpoint)
    rewrite_checkpoint(tmp_path, checkpoint)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_wayback_replay_state.py"), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "boundary registry" in result.stderr


def test_tampered_boundary_registry_cannot_be_resealed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = json.loads(replay_module.BOUNDARY_REGISTRY_PATH.read_text())
    registry["profiles"][0]["archive_hosts"] = ["righttoknow.example"]
    path = tmp_path / "tampered-boundary-registry.json"
    path.write_text(json.dumps(registry), encoding="utf-8")
    monkeypatch.setattr(replay_module, "BOUNDARY_REGISTRY_PATH", path)
    config = configuration()
    config["boundary_registry_sha256"] = sha256_bytes(path.read_bytes())
    with pytest.raises(ReplayStateError, match="registry pin"):
        validate_configuration(config)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("floor_seconds", 0),
        ("ceiling_seconds", 0),
        ("backoff_multiplier", 0.5),
        ("circuit_seconds", -1),
        ("minimum_window", 5),
    ],
)
def test_producer_and_independent_verifier_reject_invalid_policy(
    tmp_path: Path, field: str, value: float
) -> None:
    config = configuration()
    config["policy"][field] = value
    repin_policy(config)
    with pytest.raises(ReplayStateError):
        validate_configuration(config)

    valid = configuration()
    checkpoint = write_initial_state(tmp_path, valid)
    persisted = json.loads((tmp_path / "configuration.json").read_text())
    persisted["policy"][field] = value
    repin_policy(persisted)
    (tmp_path / "configuration.json").write_text(json.dumps(persisted))
    checkpoint["replay_policy_sha256"] = persisted["replay_policy_sha256"]
    checkpoint["configuration_sha256"] = content_hash(persisted)
    checkpoint.pop("checkpoint_sha256")
    checkpoint["checkpoint_sha256"] = content_hash(checkpoint)
    rewrite_checkpoint(tmp_path, checkpoint)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_wayback_replay_state.py"), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "policy" in result.stderr.lower() or "schema" in result.stderr.lower()


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
def test_replacement_candidates_reject_any_url_change(tmp_path: Path, url: str) -> None:
    config = configuration()
    metadata_path, metadata_sha256, row_sha256, evidence_path, evidence_sha256 = (
        approved_cdx_evidence()
    )
    checkpoint = {
        "checkpoint_sha256": "c" * 64,
        "member_states": {"synthetic-001": "terminal"},
    }
    with pytest.raises(ReplayStateError):
        replacement_candidate(
            configuration=config,
            checkpoint=checkpoint,
            member_id="synthetic-001",
            candidate_url=url,
            capture_timestamp="2025-01-01T00:00:00Z",
            source_metadata_path=metadata_path,
            source_metadata_sha256=metadata_sha256,
            source_row_sha256=row_sha256,
            retrieval_evidence_path=evidence_path,
            retrieval_evidence_sha256=evidence_sha256,
        )


def test_candidate_cannot_activate_replay_membership(tmp_path: Path) -> None:
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    checkpoint = record_observation(
        root=tmp_path,
        configuration=config,
        checkpoint=checkpoint,
        member_id="synthetic-001",
        occurrence_id="terminal-404",
        attempt_number=1,
        observation=ReplayObservation(kind="http", status_code=404),
        now=NOW,
        rng=random.Random(1),
    )
    before = json.loads(json.dumps(checkpoint))
    metadata_path, metadata_sha256, row_sha256, evidence_path, evidence_sha256 = (
        approved_cdx_evidence()
    )
    candidate = replacement_candidate(
        configuration=config,
        checkpoint=checkpoint,
        member_id="synthetic-001",
        candidate_url=config["members"][0]["canonical_url"],
        capture_timestamp="2025-01-01T00:00:00Z",
        source_metadata_path=metadata_path,
        source_metadata_sha256=metadata_sha256,
        source_row_sha256=row_sha256,
        retrieval_evidence_path=evidence_path,
        retrieval_evidence_sha256=evidence_sha256,
    )
    assert candidate["status"] == "pending_replay_approval"
    assert candidate["configuration_sha256"] == content_hash(config)
    assert candidate["checkpoint_sha256"] == checkpoint["checkpoint_sha256"]
    assert candidate["failed_status"] == "terminal"
    assert checkpoint["counts"]["population"] == 2
    assert list(checkpoint["member_states"]) == ["synthetic-001", "synthetic-002"]
    assert checkpoint == before


@pytest.mark.parametrize("member_id", ["invented", "synthetic-002"])
def test_replacement_candidate_rejects_arbitrary_or_nonfailed_member(
    tmp_path: Path, member_id: str
) -> None:
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    metadata_path, metadata_sha256, row_sha256 = write_cdx_metadata(
        tmp_path,
        member_id=member_id,
        canonical_url="https://example.test/request/synthetic-002",
    )
    evidence_path = APPROVED_CDX_EVIDENCE
    evidence_sha256 = sha256_bytes(evidence_path.read_bytes())
    with pytest.raises(ReplayStateError, match=r"failed member|configured population"):
        replacement_candidate(
            configuration=config,
            checkpoint=checkpoint,
            member_id=member_id,
            candidate_url="https://example.test/request/synthetic-002",
            capture_timestamp="2025-01-01T00:00:00Z",
            source_metadata_path=metadata_path,
            source_metadata_sha256=metadata_sha256,
            source_row_sha256=row_sha256,
            retrieval_evidence_path=evidence_path,
            retrieval_evidence_sha256=evidence_sha256,
        )


def test_replacement_merge_rejects_wrong_configuration_or_checkpoint(tmp_path: Path) -> None:
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    checkpoint = record_observation(
        root=tmp_path,
        configuration=config,
        checkpoint=checkpoint,
        member_id="synthetic-001",
        occurrence_id="terminal-404",
        attempt_number=1,
        observation=ReplayObservation(kind="http", status_code=404),
        now=NOW,
        rng=random.Random(1),
    )
    metadata_path, metadata_sha256, row_sha256, evidence_path, evidence_sha256 = (
        approved_cdx_evidence()
    )
    candidate = replacement_candidate(
        configuration=config,
        checkpoint=checkpoint,
        member_id="synthetic-001",
        candidate_url=config["members"][0]["canonical_url"],
        capture_timestamp="2025-01-01T00:00:00Z",
        source_metadata_path=metadata_path,
        source_metadata_sha256=metadata_sha256,
        source_row_sha256=row_sha256,
        retrieval_evidence_path=evidence_path,
        retrieval_evidence_sha256=evidence_sha256,
    )
    changed = configuration()
    changed["producer_version"] = "changed"
    with pytest.raises(ReplayStateError, match="configuration"):
        merge_replacement_candidates([candidate], configuration=changed, checkpoint=checkpoint)
    other_checkpoint = dict(checkpoint)
    other_checkpoint["checkpoint_sha256"] = "d" * 64
    with pytest.raises(ReplayStateError, match="checkpoint"):
        merge_replacement_candidates([candidate], configuration=config, checkpoint=other_checkpoint)
    changed_url = dict(candidate)
    changed_url["canonical_url"] = "https://example.test/request/other"
    changed_url.pop("candidate_sha256")
    changed_url["candidate_sha256"] = content_hash(changed_url)
    with pytest.raises(ReplayStateError, match="exact URL"):
        merge_replacement_candidates([changed_url], configuration=config, checkpoint=checkpoint)


def test_replacement_candidate_rejects_fabricated_or_unbound_cdx_metadata(
    tmp_path: Path,
) -> None:
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    checkpoint = record_observation(
        root=tmp_path,
        configuration=config,
        checkpoint=checkpoint,
        member_id="synthetic-001",
        occurrence_id="terminal-for-cdx-check",
        attempt_number=1,
        observation=ReplayObservation(kind="http", status_code=404),
        now=NOW,
        rng=random.Random(1),
    )
    path, artifact_sha256, row_sha256 = write_cdx_metadata(
        tmp_path,
        capture_timestamp="2099-01-01T00:00:00Z",
    )
    evidence_path = APPROVED_CDX_EVIDENCE
    evidence_sha256 = sha256_bytes(evidence_path.read_bytes())
    for mutation in ("artifact_hash", "row_hash", "timestamp", "member"):
        kwargs: dict[str, object] = {
            "configuration": config,
            "checkpoint": checkpoint,
            "member_id": "synthetic-001",
            "candidate_url": config["members"][0]["canonical_url"],
            "capture_timestamp": "2025-01-01T00:00:00Z",
            "source_metadata_path": path,
            "source_metadata_sha256": artifact_sha256,
            "source_row_sha256": row_sha256,
            "retrieval_evidence_path": evidence_path,
            "retrieval_evidence_sha256": evidence_sha256,
        }
        if mutation == "artifact_hash":
            kwargs["source_metadata_sha256"] = "a" * 64
        elif mutation == "row_hash":
            kwargs["source_row_sha256"] = "b" * 64
        elif mutation == "timestamp":
            kwargs["capture_timestamp"] = "2025-01-02T00:00:00Z"
        else:
            kwargs["member_id"] = "synthetic-002"
        with pytest.raises(ReplayStateError):
            replacement_candidate(**kwargs)  # type: ignore[arg-type]


def test_self_hashed_caller_supplied_cdx_artifact_cannot_qualify(
    tmp_path: Path,
) -> None:
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    checkpoint = record_observation(
        root=tmp_path,
        configuration=config,
        checkpoint=checkpoint,
        member_id="synthetic-001",
        occurrence_id="terminal-for-forged-cdx",
        attempt_number=1,
        observation=ReplayObservation(kind="http", status_code=404),
        now=NOW,
        rng=random.Random(1),
    )
    metadata_path, metadata_sha256, row_sha256 = write_cdx_metadata(tmp_path)
    evidence_path = APPROVED_CDX_EVIDENCE
    evidence_sha256 = sha256_bytes(evidence_path.read_bytes())

    with pytest.raises(ReplayStateError, match="approved CDX artifact registry"):
        replacement_candidate(
            configuration=config,
            checkpoint=checkpoint,
            member_id="synthetic-001",
            candidate_url=config["members"][0]["canonical_url"],
            capture_timestamp="2025-01-01T00:00:00Z",
            source_metadata_path=metadata_path,
            source_metadata_sha256=metadata_sha256,
            source_row_sha256=row_sha256,
            retrieval_evidence_path=evidence_path,
            retrieval_evidence_sha256=evidence_sha256,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("endpoint", "https://example.test/cdx"),
        ("query_scope", "https://example.test/request/other.json"),
        ("producer_id", "caller-controlled-producer"),
        ("retrieved_at", "2026-08-01T00:00:00Z"),
    ],
)
def test_self_hashed_retrieval_receipt_cannot_redefine_provenance(
    tmp_path: Path, field: str, value: str
) -> None:
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    checkpoint = record_observation(
        root=tmp_path,
        configuration=config,
        checkpoint=checkpoint,
        member_id="synthetic-001",
        occurrence_id=f"terminal-for-forged-{field}",
        attempt_number=1,
        observation=ReplayObservation(kind="http", status_code=404),
        now=NOW,
        rng=random.Random(1),
    )
    metadata_path, metadata_sha256, row_sha256, evidence_path, _ = approved_cdx_evidence()
    forged = json.loads(evidence_path.read_text())
    forged[field] = value
    forged_path = tmp_path / f"forged-{field}.json"
    forged_path.write_text(json.dumps(forged, separators=(",", ":"), sort_keys=True))

    with pytest.raises(ReplayStateError, match="approved CDX artifact registry"):
        replacement_candidate(
            configuration=config,
            checkpoint=checkpoint,
            member_id="synthetic-001",
            candidate_url=config["members"][0]["canonical_url"],
            capture_timestamp="2025-01-01T00:00:00Z",
            source_metadata_path=metadata_path,
            source_metadata_sha256=metadata_sha256,
            source_row_sha256=row_sha256,
            retrieval_evidence_path=forged_path,
            retrieval_evidence_sha256=sha256_bytes(forged_path.read_bytes()),
        )


def test_approval_registry_cannot_be_replaced_and_resealed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = json.loads(approval_module.APPROVAL_REGISTRY_PATH.read_text())
    registry["approvals"][0]["producer_id"] = "caller-controlled-producer"
    forged_registry = tmp_path / "forged-approval-registry.json"
    forged_registry.write_text(json.dumps(registry, separators=(",", ":"), sort_keys=True))
    monkeypatch.setattr(approval_module, "APPROVAL_REGISTRY_PATH", forged_registry)
    metadata_path, metadata_sha256, _, evidence_path, evidence_sha256 = approved_cdx_evidence()

    with pytest.raises(approval_module.CdxApprovalError, match="registry pin"):
        approval_module.load_approved_cdx_evidence(
            artifact_path=metadata_path,
            artifact_sha256=metadata_sha256,
            retrieval_evidence_path=evidence_path,
            retrieval_evidence_sha256=evidence_sha256,
        )


def test_resealed_candidate_cannot_redefine_registered_provenance(tmp_path: Path) -> None:
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    checkpoint = record_observation(
        root=tmp_path,
        configuration=config,
        checkpoint=checkpoint,
        member_id="synthetic-001",
        occurrence_id="terminal-for-candidate-provenance",
        attempt_number=1,
        observation=ReplayObservation(kind="http", status_code=404),
        now=NOW,
        rng=random.Random(1),
    )
    metadata_path, metadata_sha256, row_sha256, evidence_path, evidence_sha256 = (
        approved_cdx_evidence()
    )
    candidate = replacement_candidate(
        configuration=config,
        checkpoint=checkpoint,
        member_id="synthetic-001",
        candidate_url=config["members"][0]["canonical_url"],
        capture_timestamp="2025-01-01T00:00:00Z",
        source_metadata_path=metadata_path,
        source_metadata_sha256=metadata_sha256,
        source_row_sha256=row_sha256,
        retrieval_evidence_path=evidence_path,
        retrieval_evidence_sha256=evidence_sha256,
    )
    candidate["producer_id"] = "caller-controlled-producer"
    candidate.pop("candidate_sha256")
    candidate["candidate_sha256"] = content_hash(candidate)

    with pytest.raises(ReplayStateError, match="approved provenance"):
        merge_replacement_candidates([candidate], configuration=config, checkpoint=checkpoint)

    candidate["producer_id"] = "fyi-archive-test-fixture"
    candidate["approval_registry_sha256"] = "0" * 64
    candidate.pop("candidate_sha256")
    candidate["candidate_sha256"] = content_hash(candidate)
    with pytest.raises(ReplayStateError, match="approval-registry pin"):
        merge_replacement_candidates([candidate], configuration=config, checkpoint=checkpoint)


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
    symlink_or_skip(link, real)
    with pytest.raises(ReplayStateError, match="symlink"):
        write_initial_state(link, configuration())


def test_producer_contains_no_network_client() -> None:
    source = (ROOT / "src" / "fyi_archive" / "wayback_replay.py").read_text()
    assert "import httpx" not in source
    assert "import requests" not in source
    assert "urlopen" not in source
    assert "ObservationTransport" in source
