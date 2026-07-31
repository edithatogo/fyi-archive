"""Positive contract tests for transport-independent replay state."""

from __future__ import annotations

import importlib.util
import json
import random
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from fyi_archive.wayback_replay import (
    ReplayObservation,
    classify_observation,
    initial_checkpoint,
    merge_replacement_candidates,
    next_pacing,
    object_path,
    parse_retry_after,
    record_observation,
    replacement_candidate,
    sha256_bytes,
    store_object,
    validate_configuration,
    verify_resume_state,
    write_initial_state,
)

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
NOW = datetime(2026, 7, 31, 0, 0, tzinfo=UTC)


def configuration() -> dict[str, Any]:
    return json.loads((FIXTURES / "wayback_replay_configuration.json").read_text())


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
    candidate = replacement_candidate(
        configuration=config,
        checkpoint=checkpoint,
        member_id=member["member_id"],
        candidate_url=member["canonical_url"],
        capture_timestamp="2025-12-31T23:59:59Z",
        source_metadata_sha256="a" * 64,
        source_row_sha256="b" * 64,
    )
    assert candidate["status"] == "pending_replay_approval"
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
