"""Positive contract tests for transport-independent replay state."""

from __future__ import annotations

import importlib.util
import json
import math
import random
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator, FormatChecker

import fyi_archive.wayback_cdx_approvals as approval_module
import fyi_archive.wayback_replay as replay_module
from fyi_archive.wayback_cdx_approvals import APPROVED_APPROVAL_REGISTRY_SHA256
from fyi_archive.wayback_replay import (
    ReplayObservation,
    ReplayStateError,
    classify_observation,
    content_hash,
    initial_checkpoint,
    merge_replacement_candidates,
    next_pacing,
    object_path,
    parse_retry_after,
    record_observation,
    replacement_candidate,
    sha256_bytes,
    store_object,
    validate_canonical_url,
    validate_configuration,
    verify_resume_state,
    write_initial_state,
)

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
NOW = datetime(2026, 7, 31, 0, 0, tzinfo=UTC)
APPROVED_CDX_METADATA = FIXTURES / "wayback-approved-cdx-metadata.json"
APPROVED_CDX_EVIDENCE = FIXTURES / "wayback-approved-cdx-retrieval-evidence.json"


def configuration() -> dict[str, Any]:
    return json.loads((FIXTURES / "wayback_replay_configuration.json").read_text())


def approved_cdx_evidence() -> tuple[Path, str, str, Path, str]:
    artifact = json.loads(APPROVED_CDX_METADATA.read_text())
    return (
        APPROVED_CDX_METADATA,
        sha256_bytes(APPROVED_CDX_METADATA.read_bytes()),
        str(artifact["rows"][0]["row_sha256"]),
        APPROVED_CDX_EVIDENCE,
        sha256_bytes(APPROVED_CDX_EVIDENCE.read_bytes()),
    )


def test_positive_configuration_and_schemas() -> None:
    config = validate_configuration(configuration())
    checkpoint = initial_checkpoint(config)
    schemas = {
        "wayback-replay-configuration.schema.json": config,
        "wayback-replay-checkpoint.schema.json": checkpoint,
    }
    for filename, instance in schemas.items():
        schema = json.loads((ROOT / "schemas" / filename).read_text())
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(instance)


def test_content_addressed_store_deduplicates_and_verifies(tmp_path: Path) -> None:
    payload = b"synthetic archived response"
    digest = store_object(tmp_path, payload)
    assert store_object(tmp_path, payload, expected_sha256=digest) == digest
    assert object_path(tmp_path, digest).read_bytes() == payload
    assert len(list((tmp_path / "objects").rglob(digest))) == 1


@pytest.mark.parametrize(
    "value", ["", "http://example.test/", "https://example.test/path#fragment"]
)
def test_canonical_url_rejects_unsafe_forms(value: str) -> None:
    with pytest.raises(ReplayStateError):
        validate_canonical_url(value)


def test_content_hash_is_stable_for_json_objects() -> None:
    assert content_hash({"b": 2, "a": 1}) == content_hash({"a": 1, "b": 2})


def test_approval_helpers_reject_malformed_inputs(tmp_path: Path) -> None:
    with pytest.raises(approval_module.CdxApprovalError, match="lowercase SHA-256"):
        approval_module.registered_cdx_approval("not-a-digest", "0" * 64)
    with pytest.raises(approval_module.CdxApprovalError, match="strict UTF-8 JSON"):
        approval_module._strict_json(b"\\xff", "fixture")
    unsafe = tmp_path / "link"
    unsafe.symlink_to(tmp_path)
    with pytest.raises(approval_module.CdxApprovalError, match="missing or unsafe"):
        approval_module._read_regular_file(unsafe, "fixture")


@pytest.mark.parametrize(
    ("scope", "url", "allowed"),
    [
        ("https://example.test/request/*", "https://example.test/request/1", True),
        ("https://example.test/request/*", "https://example.test/other/1", False),
        ("https://example.test/request/1", "https://example.test/request/1", True),
        ("https://example.test/request/1", "https://example.test/request/2", False),
    ],
)
def test_query_scope_is_exact_or_prefix_bound(scope: str, url: str, allowed: bool) -> None:
    assert approval_module.query_scope_allows_url(scope, url) is allowed


@pytest.mark.parametrize(
    ("helper", "value", "message"),
    [
        (replay_module._require_sha256, "bad", "lowercase SHA-256"),
        (replay_module._number, True, "must be a number"),
        (replay_module._number, math.nan, "must be finite"),
        (replay_module._integer, True, "must be an integer"),
    ],
)
def test_replay_scalar_guards_reject_invalid_values(helper, value, message: str) -> None:
    with pytest.raises(ReplayStateError, match=message):
        helper(value, "field")


def test_replay_filesystem_guards_reject_unsafe_paths(tmp_path: Path) -> None:
    regular = tmp_path / "regular"
    regular.write_text("x")
    with pytest.raises(ReplayStateError, match="not a directory"):
        replay_module._require_plain_directory(regular)
    link = tmp_path / "link"
    link.symlink_to(tmp_path)
    with pytest.raises(ReplayStateError, match="symlink"):
        replay_module._require_plain_directory(link)
    with pytest.raises(ReplayStateError, match="lowercase SHA-256"):
        store_object(tmp_path / "objects", b"x", expected_sha256="bad")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("members", [], "validation failed"),
        ("jitter_seed", "seed", "validation failed"),
        ("producer", "", "validation failed"),
    ],
)
def test_configuration_rejects_contract_violations(field: str, value: object, message: str) -> None:
    config = configuration()
    config[field] = value
    if field == "members":
        config["selection_sha256"] = content_hash(value)
    with pytest.raises(ReplayStateError, match=message):
        validate_configuration(config)


@pytest.mark.parametrize(
    "observation",
    [
        ReplayObservation(kind="success", response_bytes=None),
        ReplayObservation(
            kind="success",
            response_bytes=b"x",
            final_url="http://web.archive.org/web/20260101000000id_/https://example.test/",
            content_type="application/json",
        ),
        ReplayObservation(
            kind="success",
            response_bytes=b"x",
            final_url="https://not-archive.test/web/20260101000000id_/https://example.test/",
            content_type="application/json",
        ),
        ReplayObservation(
            kind="success",
            response_bytes=b"x",
            final_url="https://web.archive.org/web/20260101000000id_/https://example.test/",
            content_type="text/plain",
        ),
    ],
)
def test_success_boundary_rejects_invalid_archive_observations(
    observation: ReplayObservation,
) -> None:
    with pytest.raises(ReplayStateError):
        classify_observation(observation, policy=configuration()["policy"])


@pytest.mark.parametrize(
    "observation",
    [
        ReplayObservation(kind="http", status_code=418),
        ReplayObservation(kind="transport", transport_code="dns"),
        ReplayObservation(kind="terminal", terminal_code="unknown"),
        ReplayObservation(kind=cast(Any, "other")),
    ],
)
def test_unregistered_observations_fail_closed(observation: ReplayObservation) -> None:
    with pytest.raises(ReplayStateError, match="unregistered"):
        classify_observation(observation, policy=configuration()["policy"])


def test_pacing_complete_and_terminal_paths_do_not_open_circuit() -> None:
    policy = configuration()["policy"]
    previous = {
        "delay_seconds": 10.0,
        "consecutive_failures": 3,
        "window": [True, False],
        "circuit_open_until": None,
    }
    for disposition in ("complete", "terminal"):
        decision = next_pacing(
            previous=previous,
            outcome=replay_module.Outcome(disposition, disposition),
            policy=policy,
            now=NOW,
            rng=random.Random(1),
        )
        assert decision.consecutive_failures == 0
        assert decision.circuit_open_until is None


def test_journal_guards_and_chain_tamper_detection(tmp_path: Path) -> None:
    path = tmp_path / "attempts.jsonl"
    with pytest.raises(ReplayStateError, match="chain fields"):
        replay_module.append_attempt(path, {"entry_sha256": "x"})
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    record_observation(
        root=tmp_path,
        configuration=config,
        checkpoint=checkpoint,
        member_id=config["members"][0]["member_id"],
        occurrence_id="journal-1",
        attempt_number=1,
        observation=ReplayObservation(kind="http", status_code=404),
        now=NOW,
        rng=random.Random(1),
    )
    path = tmp_path / "attempts.jsonl"
    count, tail, entries = replay_module.verify_journal(path)
    assert count == 1
    assert tail == entries[-1]["entry_sha256"]
    path.write_bytes(
        path.read_bytes().replace(b'"outcome_code":"http_404"', b'"outcome_code":"http_410"')
    )
    with pytest.raises(ReplayStateError):
        replay_module.verify_journal(path)


def test_missing_journal_is_empty(tmp_path: Path) -> None:
    assert replay_module.verify_journal(tmp_path / "missing.jsonl") == (0, None, [])


def test_write_record_resume_and_independent_verifier(tmp_path: Path) -> None:
    config = configuration()
    checkpoint = write_initial_state(tmp_path, config)
    checkpoint = record_observation(
        root=tmp_path,
        configuration=config,
        checkpoint=checkpoint,
        member_id="synthetic-001",
        occurrence_id="run-1/member-1/attempt-1",
        attempt_number=1,
        observation=ReplayObservation(
            kind="success",
            response_bytes=b'{"synthetic":true}',
            response_sha256=sha256_bytes(b'{"synthetic":true}'),
            final_url="https://web.archive.org/web/20260101000000id_/https://example.test/",
            content_type="application/json",
        ),
        now=NOW,
        rng=random.Random(20260731),
    )
    checkpoint = record_observation(
        root=tmp_path,
        configuration=config,
        checkpoint=checkpoint,
        member_id="synthetic-002",
        occurrence_id="run-1/member-2/attempt-1",
        attempt_number=1,
        observation=ReplayObservation(kind="http", status_code=503, retry_after="5"),
        now=NOW,
        rng=random.Random(20260731),
    )
    verified, entries = verify_resume_state(tmp_path, config, checkpoint)
    assert verified["counts"] == {
        "population": 2,
        "pending": 0,
        "complete": 1,
        "retryable": 1,
        "terminal": 0,
        "replacement_candidates": 0,
    }
    assert [entry["outcome_code"] for entry in entries] == ["success", "http_503"]
    attempt_schema = json.loads(
        (ROOT / "schemas" / "wayback-replay-attempt.schema.json").read_text()
    )
    validator = Draft202012Validator(attempt_schema, format_checker=FormatChecker())
    for entry in entries:
        validator.validate(entry)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_wayback_replay_state.py"), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["valid"] is True
    assert report["population"] == 2
    assert report["journal_entries"] == 2


@pytest.mark.parametrize(
    ("observation", "code", "disposition"),
    [
        (
            ReplayObservation(
                kind="success",
                response_bytes=b"x",
                final_url="https://web.archive.org/web/20260101000000id_/https://example.test/",
                content_type="application/json",
            ),
            "success",
            "complete",
        ),
        (ReplayObservation(kind="http", status_code=429), "http_429", "retryable"),
        (ReplayObservation(kind="http", status_code=500), "http_500", "retryable"),
        (ReplayObservation(kind="http", status_code=502), "http_502", "retryable"),
        (ReplayObservation(kind="http", status_code=503), "http_503", "retryable"),
        (ReplayObservation(kind="http", status_code=504), "http_504", "retryable"),
        (ReplayObservation(kind="http", status_code=404), "http_404", "terminal"),
        (ReplayObservation(kind="http", status_code=410), "http_410", "terminal"),
        (ReplayObservation(kind="transport", transport_code="timeout"), "timeout", "retryable"),
        (
            ReplayObservation(kind="transport", transport_code="connection"),
            "connection",
            "retryable",
        ),
        (
            ReplayObservation(kind="terminal", terminal_code="redirect_escape"),
            "redirect_escape",
            "terminal",
        ),
        (
            ReplayObservation(kind="terminal", terminal_code="payload_too_large"),
            "payload_too_large",
            "terminal",
        ),
        (
            ReplayObservation(kind="terminal", terminal_code="scope_violation"),
            "scope_violation",
            "terminal",
        ),
        (
            ReplayObservation(kind="terminal", terminal_code="unsupported_content_type"),
            "unsupported_content_type",
            "terminal",
        ),
        (
            ReplayObservation(kind="terminal", terminal_code="malformed_content"),
            "malformed_content",
            "terminal",
        ),
    ],
)
def test_typed_outcomes(observation, code: str, disposition: str) -> None:
    outcome = classify_observation(observation, policy=configuration()["policy"])
    assert (outcome.code, outcome.retry_disposition) == (code, disposition)


def test_integrity_mismatch_is_terminal() -> None:
    outcome = classify_observation(
        ReplayObservation(
            kind="success",
            response_bytes=b"x",
            response_sha256="0" * 64,
            final_url="https://web.archive.org/web/20260101000000id_/https://example.test/",
            content_type="application/json",
        ),
        policy=configuration()["policy"],
    )
    assert outcome.code == "integrity_mismatch"
    assert outcome.retry_disposition == "terminal"


def test_retry_after_seconds_date_and_cap() -> None:
    assert parse_retry_after("15", now=NOW, ceiling_seconds=60) == 15
    assert parse_retry_after("999", now=NOW, ceiling_seconds=60) == 60
    assert parse_retry_after("Fri, 31 Jul 2026 00:00:20 GMT", now=NOW, ceiling_seconds=60) == 20
    assert parse_retry_after("not-a-date", now=NOW, ceiling_seconds=60) is None


def test_pacing_is_seeded_adaptive_and_opens_circuit() -> None:
    policy = configuration()["policy"]
    previous = {
        "delay_seconds": 1.0,
        "consecutive_failures": 2,
        "window": [True, True],
        "circuit_open_until": None,
    }
    first = next_pacing(
        previous=previous,
        outcome=classify_observation(ReplayObservation(kind="http", status_code=503)),
        policy=policy,
        now=NOW,
        rng=random.Random(7),
        retry_after="5",
    )
    second = next_pacing(
        previous=previous,
        outcome=classify_observation(ReplayObservation(kind="http", status_code=503)),
        policy=policy,
        now=NOW,
        rng=random.Random(7),
        retry_after="5",
    )
    assert first == second
    assert first.delay_seconds >= 5
    assert first.circuit_open_until == "2026-07-31T00:02:00Z"
    success = next_pacing(
        previous={
            "delay_seconds": first.delay_seconds,
            "consecutive_failures": first.consecutive_failures,
            "window": first.window,
            "circuit_open_until": first.circuit_open_until,
        },
        outcome=classify_observation(
            ReplayObservation(
                kind="success",
                response_bytes=b"x",
                final_url="https://web.archive.org/web/20260101000000id_/https://example.test/",
                content_type="application/json",
            ),
            policy=policy,
        ),
        policy=policy,
        now=NOW,
        rng=random.Random(7),
    )
    assert success.delay_seconds >= policy["floor_seconds"]
    assert success.delay_seconds < first.delay_seconds
    assert success.consecutive_failures == 0
    assert success.circuit_open_until is None


def test_replacement_candidate_is_exact_pinned_pending_and_deduplicated(tmp_path: Path) -> None:
    config = configuration()
    member = config["members"][0]
    checkpoint = write_initial_state(tmp_path, config)
    checkpoint = record_observation(
        root=tmp_path,
        configuration=config,
        checkpoint=checkpoint,
        member_id=member["member_id"],
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
        member_id=member["member_id"],
        candidate_url=member["canonical_url"],
        capture_timestamp="2025-01-01T00:00:00Z",
        source_metadata_path=metadata_path,
        source_metadata_sha256=metadata_sha256,
        source_row_sha256=row_sha256,
        retrieval_evidence_path=evidence_path,
        retrieval_evidence_sha256=evidence_sha256,
    )
    assert candidate["status"] == "pending_replay_approval"
    assert candidate["approval_registry_sha256"] == APPROVED_APPROVAL_REGISTRY_SHA256
    assert merge_replacement_candidates(
        [candidate, candidate], configuration=config, checkpoint=checkpoint
    ) == [candidate]
    schema = json.loads(
        (ROOT / "schemas" / "wayback-replacement-candidate.schema.json").read_text()
    )
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(candidate)


def test_frozen_au_oracle_is_metadata_only_and_conserved() -> None:
    oracle = json.loads((FIXTURES / "au_rtk_replay_oracle.json").read_text())
    population = oracle["population"]
    assert population["successful"] + population["explicit_http_404"] == population["selected"]
    assert "no_restricted_content" in oracle["restrictions"]
    assert "not_authorization" in oracle["restrictions"]


def test_independent_verifier_imports_no_producer() -> None:
    path = ROOT / "scripts" / "verify_wayback_replay_state.py"
    source = path.read_text()
    assert "from fyi_archive" not in source
    assert "import fyi_archive" not in source
    spec = importlib.util.spec_from_file_location("independent_wayback_verifier", path)
    assert spec is not None
