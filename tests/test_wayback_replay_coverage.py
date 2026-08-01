"""Focused fail-closed coverage for Wayback replay and CDX approval boundaries."""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import fyi_archive.wayback_cdx_approvals as approvals
import fyi_archive.wayback_replay as replay

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
CONFIGURATION = FIXTURES / "wayback_replay_configuration.json"
CDX_METADATA = FIXTURES / "wayback-approved-cdx-metadata.json"
CDX_EVIDENCE = FIXTURES / "wayback-approved-cdx-retrieval-evidence.json"
NOW = datetime(2026, 7, 31, tzinfo=UTC)


def configuration() -> dict[str, Any]:
    return json.loads(CONFIGURATION.read_text())


def repin_policy(config: dict[str, Any]) -> None:
    config["replay_policy_sha256"] = replay.content_hash(config["policy"])


def write_json(path: Path, value: object) -> None:
    path.write_bytes(replay.canonical_json(value))


def symlink_or_skip(link: Path, target: Path) -> None:
    """Create a symlink or skip where the platform policy forbids it."""
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except OSError as error:
        pytest.skip(f"symlink creation is unavailable: {error}")


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b'{"key":1,"key":2}', "duplicate key"),
        (b'{"value":NaN}', "non-finite number"),
        (b"\xff", "strict UTF-8 JSON"),
        (b"{", "strict UTF-8 JSON"),
    ],
)
def test_strict_cdx_json_rejects_ambiguous_encodings(raw: bytes, message: str) -> None:
    with pytest.raises(approvals.CdxApprovalError, match=message):
        approvals._strict_json(raw, "candidate")


def test_cdx_schema_and_digest_validation_fail_closed() -> None:
    with pytest.raises(approvals.CdxApprovalError, match="validation failed"):
        approvals._validate_schema("wayback-cdx-approval-registry.schema.json", {})
    with pytest.raises(approvals.CdxApprovalError, match="lowercase SHA-256"):
        approvals._require_digest("A" * 64, "digest")


def test_cdx_file_boundary_rejects_missing_symlink_and_read_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(approvals.CdxApprovalError, match="missing or unsafe"):
        approvals._read_regular_file(missing, "candidate")

    target = tmp_path / "target.json"
    target.write_text("{}")
    link = tmp_path / "link.json"
    symlink_or_skip(link, target)
    with pytest.raises(approvals.CdxApprovalError, match="missing or unsafe"):
        approvals._read_regular_file(link, "candidate")

    monkeypatch.setattr(Path, "read_bytes", lambda _path: (_ for _ in ()).throw(OSError()))
    with pytest.raises(approvals.CdxApprovalError, match="unreadable"):
        approvals._read_regular_file(target, "candidate")


def test_registered_cdx_approval_rejects_duplicate_registry_identities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = json.loads(approvals.APPROVAL_REGISTRY_PATH.read_text())
    registry["approvals"].append(dict(registry["approvals"][0]))
    path = tmp_path / "registry.json"
    write_json(path, registry)
    monkeypatch.setattr(approvals, "APPROVAL_REGISTRY_PATH", path)
    monkeypatch.setattr(
        approvals,
        "APPROVED_APPROVAL_REGISTRY_SHA256",
        approvals._sha256_bytes(path.read_bytes()),
    )
    entry = registry["approvals"][0]
    with pytest.raises(approvals.CdxApprovalError, match="identities are not unique"):
        approvals.registered_cdx_approval(
            entry["artifact_sha256"], entry["retrieval_evidence_sha256"]
        )


def test_registered_cdx_approval_rejects_absent_pair() -> None:
    with pytest.raises(approvals.CdxApprovalError, match="absent or ambiguous"):
        approvals.registered_cdx_approval("0" * 64, "1" * 64)


@pytest.mark.parametrize("target", ["artifact", "evidence"])
def test_approved_cdx_evidence_rejects_hash_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    artifact = tmp_path / "artifact.json"
    evidence = tmp_path / "evidence.json"
    artifact.write_bytes(CDX_METADATA.read_bytes())
    evidence.write_bytes(CDX_EVIDENCE.read_bytes())
    approval = json.loads(approvals.APPROVAL_REGISTRY_PATH.read_text())["approvals"][0]
    approval = dict(approval)
    if target == "artifact":
        approval["artifact_sha256"] = "0" * 64
    else:
        approval["retrieval_evidence_sha256"] = "0" * 64
    monkeypatch.setattr(approvals, "registered_cdx_approval", lambda *_args: approval)
    with pytest.raises(approvals.CdxApprovalError, match="hash does not match"):
        approvals.load_approved_cdx_evidence(
            artifact_path=artifact,
            artifact_sha256="a" * 64,
            retrieval_evidence_path=evidence,
            retrieval_evidence_sha256="b" * 64,
        )


def test_approved_cdx_evidence_rejects_unbound_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "artifact.json"
    evidence = tmp_path / "evidence.json"
    artifact.write_bytes(CDX_METADATA.read_bytes())
    evidence_value = json.loads(CDX_EVIDENCE.read_text())
    evidence_value["artifact_sha256"] = "0" * 64
    write_json(evidence, evidence_value)
    approval = json.loads(approvals.APPROVAL_REGISTRY_PATH.read_text())["approvals"][0]
    approval = dict(approval)
    approval["artifact_sha256"] = approvals._sha256_bytes(artifact.read_bytes())
    approval["retrieval_evidence_sha256"] = approvals._sha256_bytes(evidence.read_bytes())
    monkeypatch.setattr(approvals, "registered_cdx_approval", lambda *_args: approval)
    with pytest.raises(approvals.CdxApprovalError, match="does not bind"):
        approvals.load_approved_cdx_evidence(
            artifact_path=artifact,
            artifact_sha256=approval["artifact_sha256"],
            retrieval_evidence_path=evidence,
            retrieval_evidence_sha256=approval["retrieval_evidence_sha256"],
        )


def test_approved_cdx_evidence_rejects_provenance_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "artifact.json"
    evidence = tmp_path / "evidence.json"
    artifact_value = json.loads(CDX_METADATA.read_text())
    artifact_value["producer_id"] = "drifted-producer"
    write_json(artifact, artifact_value)
    evidence_value = json.loads(CDX_EVIDENCE.read_text())
    evidence_value["artifact_sha256"] = approvals._sha256_bytes(artifact.read_bytes())
    write_json(evidence, evidence_value)
    approval = dict(json.loads(approvals.APPROVAL_REGISTRY_PATH.read_text())["approvals"][0])
    approval["artifact_sha256"] = approvals._sha256_bytes(artifact.read_bytes())
    approval["retrieval_evidence_sha256"] = approvals._sha256_bytes(evidence.read_bytes())
    monkeypatch.setattr(approvals, "registered_cdx_approval", lambda *_args: approval)
    with pytest.raises(approvals.CdxApprovalError, match="provenance differs"):
        approvals.load_approved_cdx_evidence(
            artifact_path=artifact,
            artifact_sha256=approval["artifact_sha256"],
            retrieval_evidence_path=evidence,
            retrieval_evidence_sha256=approval["retrieval_evidence_sha256"],
        )


def test_query_scope_requires_exact_or_prefix_match() -> None:
    assert approvals.query_scope_allows_url(
        "https://example.test/request/*", "https://example.test/request/1"
    )
    assert not approvals.query_scope_allows_url(
        "https://example.test/request/*", "https://example.test/other/1"
    )
    assert approvals.query_scope_allows_url(
        "https://example.test/request/1", "https://example.test/request/1"
    )
    assert not approvals.query_scope_allows_url(
        "https://example.test/request/1", "https://example.test/request/2"
    )


@pytest.mark.parametrize(
    ("function", "value", "message"),
    [
        (replay._number, True, "must be a number"),
        (replay._number, float("inf"), "must be finite"),
        (replay._integer, True, "must be an integer"),
    ],
)
def test_numeric_boundaries_reject_bool_and_nonfinite(function, value, message: str) -> None:
    with pytest.raises(replay.ReplayStateError, match=message):
        function(value, "field")


def test_directory_boundary_rejects_nondirectory(tmp_path: Path) -> None:
    path = tmp_path / "state"
    path.write_text("not a directory")
    with pytest.raises(replay.ReplayStateError, match="not a directory"):
        replay._require_plain_directory(path)


def test_store_rejects_expected_hash_and_postwrite_corruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(replay.ReplayStateError, match="expected SHA-256"):
        replay.store_object(tmp_path, b"payload", expected_sha256="0" * 64)

    def corrupt_write(path: Path, _payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"corrupt")

    monkeypatch.setattr(replay, "_atomic_write", corrupt_write)
    with pytest.raises(replay.ReplayStateError, match="integrity verification"):
        replay.store_object(tmp_path / "other", b"payload")


@pytest.mark.parametrize(
    "url",
    [
        "http://example.test/request/1",
        "https://example.test:444/request/1",
        "https://example.test/a/../b",
        "https://example.test/a/./b",
    ],
)
def test_canonical_url_validation_rejects_unsafe_forms(url: str) -> None:
    with pytest.raises(replay.ReplayStateError):
        replay.validate_canonical_url(url)


@pytest.mark.parametrize(
    ("member", "message"),
    [
        (
            {"canonical_url": "https://example.test", "capture_timestamp": "2026-01-01T00:00:00Z"},
            "member_id",
        ),
        (
            {"member_id": "x", "canonical_url": "https://example.test", "capture_timestamp": "bad"},
            "ISO date-time",
        ),
        (
            {
                "member_id": "x",
                "canonical_url": "https://example.test",
                "capture_timestamp": "2026-01-01T00:00:00",
            },
            "timezone",
        ),
    ],
)
def test_member_validation_rejects_missing_or_ambiguous_identity(member, message: str) -> None:
    with pytest.raises(replay.ReplayStateError, match=message):
        replay._validate_member(member)


@pytest.mark.parametrize(
    ("value", "message"),
    [("bad", "ISO date-time"), ("2026-01-01T00:00:00", "timezone")],
)
def test_required_datetime_rejects_invalid_values(value: str, message: str) -> None:
    with pytest.raises(replay.ReplayStateError, match=message):
        replay._require_datetime(value, "timestamp")


def test_boundary_registry_rejects_missing_unreadable_and_unknown_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "missing.json"
    monkeypatch.setattr(replay, "BOUNDARY_REGISTRY_PATH", missing)
    with pytest.raises(replay.ReplayStateError, match="missing or unsafe"):
        replay._load_boundary_profile("0" * 64, "profile")

    unreadable = tmp_path / "unreadable.json"
    unreadable.write_bytes(b"{")
    monkeypatch.setattr(replay, "BOUNDARY_REGISTRY_PATH", unreadable)
    with pytest.raises(replay.ReplayStateError, match="unreadable"):
        replay._load_boundary_profile("0" * 64, "profile")

    registry = json.loads(
        (ROOT / "src/fyi_archive/data/wayback_replay_boundary_registry.json").read_text()
    )
    valid = tmp_path / "valid.json"
    write_json(valid, registry)
    monkeypatch.setattr(replay, "BOUNDARY_REGISTRY_PATH", valid)
    digest = replay.sha256_bytes(valid.read_bytes())
    monkeypatch.setattr(replay, "APPROVED_BOUNDARY_REGISTRY_SHA256", digest)
    with pytest.raises(replay.ReplayStateError, match="profile is not approved"):
        replay._load_boundary_profile(digest, "unknown")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("extra_field", "fields do not match"),
        ("schema", "unsupported"),
        ("members_type", "non-empty ordered array"),
        ("member_type", "must be an object"),
        ("duplicate_member", "must be unique"),
        ("policy_type", "must be an object"),
        ("integer_zero", "positive integer"),
        ("jitter", "between zero and one"),
        ("failure_ratio", "between zero and one"),
        ("decay", r"in \(0, 1\]"),
        ("floor_over_ceiling", "floor exceeds ceiling"),
        ("floor_nonpositive", "floor_seconds must be positive"),
        ("backoff", "backoff_multiplier must be at least one"),
        ("circuit", "circuit_seconds must be nonnegative"),
        ("producer", "producer is required"),
        ("jitter_seed", "jitter_seed must be an integer"),
    ],
)
def test_configuration_semantics_fail_closed_beyond_schema(
    monkeypatch: pytest.MonkeyPatch, mutation: str, message: str
) -> None:
    config = configuration()
    monkeypatch.setattr(replay, "_validate_schema", lambda *_args: None)
    if mutation == "extra_field":
        config["extra"] = True
    elif mutation == "schema":
        config["schema"] = "unknown"
    elif mutation == "members_type":
        config["members"] = []
    elif mutation == "member_type":
        config["members"] = ["not-an-object"]
    elif mutation == "duplicate_member":
        config["members"] = [config["members"][0], config["members"][0]]
        config["selection_sha256"] = replay.content_hash(config["members"])
    elif mutation == "policy_type":
        config["policy"] = "not-an-object"
    elif mutation == "integer_zero":
        config["policy"]["window_size"] = 0
        repin_policy(config)
    elif mutation == "jitter":
        config["policy"]["jitter_fraction"] = 2
        repin_policy(config)
    elif mutation == "failure_ratio":
        config["policy"]["failure_ratio"] = -1
        repin_policy(config)
    elif mutation == "decay":
        config["policy"]["decay_factor"] = 2
        repin_policy(config)
    elif mutation == "floor_over_ceiling":
        config["policy"]["floor_seconds"] = 61
        repin_policy(config)
    elif mutation == "floor_nonpositive":
        config["policy"]["floor_seconds"] = 0
        repin_policy(config)
    elif mutation == "backoff":
        config["policy"]["backoff_multiplier"] = 0.5
        repin_policy(config)
    elif mutation == "circuit":
        config["policy"]["circuit_seconds"] = -1
        repin_policy(config)
    elif mutation == "producer":
        config["producer"] = ""
    else:
        config["jitter_seed"] = "not-an-integer"
    with pytest.raises(replay.ReplayStateError, match=message):
        replay.validate_configuration(config)


def test_checkpoint_rejects_invalid_structural_state(monkeypatch: pytest.MonkeyPatch) -> None:
    config = configuration()
    checkpoint = replay.initial_checkpoint(config)
    monkeypatch.setattr(replay, "_validate_schema", lambda *_args: None)

    changed = json.loads(json.dumps(checkpoint))
    changed["member_states"] = {"synthetic-002": "pending", "synthetic-001": "pending"}
    changed.pop("checkpoint_sha256")
    changed["checkpoint_sha256"] = replay.content_hash(changed)
    with pytest.raises(replay.ReplayStateError, match="membership or ordering"):
        replay.verify_checkpoint(changed, config)

    changed = json.loads(json.dumps(checkpoint))
    changed["member_states"]["synthetic-001"] = "unknown"
    changed.pop("checkpoint_sha256")
    changed["checkpoint_sha256"] = replay.content_hash(changed)
    with pytest.raises(replay.ReplayStateError, match="invalid member state"):
        replay.verify_checkpoint(changed, config)

    changed = json.loads(json.dumps(checkpoint))
    changed["counts"]["replacement_candidates"] = -1
    changed.pop("checkpoint_sha256")
    changed["checkpoint_sha256"] = replay.content_hash(changed)
    with pytest.raises(replay.ReplayStateError, match="candidate count"):
        replay.verify_checkpoint(changed, config)

    changed = json.loads(json.dumps(checkpoint))
    changed["counts"] = "not-an-object"
    changed.pop("checkpoint_sha256")
    changed["checkpoint_sha256"] = replay.content_hash(changed)
    with pytest.raises(replay.ReplayStateError, match="counts are missing"):
        replay.verify_checkpoint(changed, config)

    changed = json.loads(json.dumps(checkpoint))
    changed["counts"]["population"] = 99
    changed.pop("checkpoint_sha256")
    changed["checkpoint_sha256"] = replay.content_hash(changed)
    with pytest.raises(replay.ReplayStateError, match="population count changed"):
        replay.verify_checkpoint(changed, config)


def test_invalid_archive_port_and_success_without_policy_fail_closed() -> None:
    observation = replay.ReplayObservation(
        kind="success",
        response_bytes=b"x",
        final_url="https://web.archive.org:bad/path",
        content_type="text/html",
    )
    with pytest.raises(replay.ReplayStateError, match="invalid final archive URL"):
        replay._validate_success_boundary(observation, configuration()["policy"])
    with pytest.raises(replay.ReplayStateError, match="validated replay policy"):
        replay.classify_observation(observation)


def test_retry_after_handles_naive_date_and_naive_now() -> None:
    assert (
        replay.parse_retry_after(
            "Fri, 31 Jul 2026 00:00:20",
            now=datetime(2026, 7, 31),  # noqa: DTZ001 - explicitly tests naive input
            ceiling_seconds=60,
        )
        == 20
    )


def test_retry_after_rejects_unparsable_nonexception_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(replay.email.utils, "parsedate_to_datetime", lambda _value: None)
    assert replay.parse_retry_after("invalid", now=NOW, ceiling_seconds=60) is None


def test_append_and_verify_journal_reject_unsafe_input(tmp_path: Path) -> None:
    journal = tmp_path / "attempts.jsonl"
    journal.mkdir()
    with pytest.raises(replay.ReplayStateError, match="not a regular file"):
        replay.append_attempt(journal, {})
    with pytest.raises(replay.ReplayStateError, match="not a regular file"):
        replay.verify_journal(journal)
    journal.rmdir()
    with pytest.raises(replay.ReplayStateError, match="chain fields"):
        replay.append_attempt(journal, {"sequence": 1})
    journal.write_bytes(b"{")
    with pytest.raises(replay.ReplayStateError, match="malformed JSON"):
        replay.verify_journal(journal)


def test_resume_rejects_missing_and_unreadable_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = configuration()
    checkpoint = replay.initial_checkpoint(config)
    with pytest.raises(replay.ReplayStateError, match="missing or unsafe"):
        replay.verify_resume_state(tmp_path, config, checkpoint)
    (tmp_path / "configuration.json").write_bytes(b"{")
    with pytest.raises(replay.ReplayStateError, match="unreadable"):
        replay.verify_resume_state(tmp_path, config, checkpoint)

    write_json(tmp_path / "configuration.json", replay.validate_configuration(config))
    original_read_text = Path.read_text

    def fail_for_configuration(path: Path, *args, **kwargs):
        if path == tmp_path / "configuration.json":
            raise OSError
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_for_configuration)
    with pytest.raises(replay.ReplayStateError, match="unreadable"):
        replay.verify_resume_state(tmp_path, config, checkpoint)


def test_record_rejects_unknown_terminal_and_invalid_attempts(tmp_path: Path) -> None:
    config = configuration()
    checkpoint = replay.write_initial_state(tmp_path, config)
    observation = replay.ReplayObservation(kind="http", status_code=404)
    rng = random.Random(1)
    with pytest.raises(replay.ReplayStateError, match="outside the configured population"):
        replay.record_observation(
            root=tmp_path,
            configuration=config,
            checkpoint=checkpoint,
            member_id="unknown",
            occurrence_id="attempt",
            attempt_number=1,
            observation=observation,
            now=NOW,
            rng=rng,
        )

    terminal = replay.record_observation(
        root=tmp_path,
        configuration=config,
        checkpoint=checkpoint,
        member_id="synthetic-001",
        occurrence_id="attempt",
        attempt_number=1,
        observation=observation,
        now=NOW,
        rng=rng,
    )
    with pytest.raises(replay.ReplayStateError, match="terminal member"):
        replay.record_observation(
            root=tmp_path,
            configuration=config,
            member_id="synthetic-001",
            checkpoint=terminal,
            occurrence_id="attempt-2",
            attempt_number=2,
            observation=observation,
            now=NOW,
            rng=rng,
        )

    with pytest.raises(replay.ReplayStateError, match="attempt number"):
        replay.record_observation(
            root=tmp_path,
            configuration=config,
            member_id="synthetic-002",
            checkpoint=terminal,
            occurrence_id="",
            attempt_number=0,
            observation=observation,
            now=NOW,
            rng=rng,
        )


def test_initial_state_refuses_overwrite(tmp_path: Path) -> None:
    replay.write_initial_state(tmp_path, configuration())
    with pytest.raises(replay.ReplayStateError, match="already exists"):
        replay.write_initial_state(tmp_path, configuration())
