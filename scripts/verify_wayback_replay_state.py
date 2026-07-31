#!/usr/bin/env python3
"""Independently verify transport-independent Wayback replay state.

This verifier deliberately imports no ``fyi_archive`` producer implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_STATES = frozenset({"pending", "complete", "retryable", "terminal"})
SCHEMA_DIRECTORY = Path(__file__).parents[1] / "schemas"


def canonical_json(value: object) -> bytes:
    """Return canonical JSON bytes."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def content_hash(value: object) -> str:
    """Hash a JSON-compatible value."""
    return hashlib.sha256(canonical_json(value)).hexdigest()


def verify_schema(filename: str, value: object) -> None:
    """Independently enforce one published replay schema."""
    schema = json.loads((SCHEMA_DIRECTORY / filename).read_text(encoding="utf-8"))
    try:
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
    except ValidationError as error:
        raise RuntimeError(f"{filename} schema validation failed: {error.message}") from error


def require_hash(value: object, field: str) -> str:
    """Require one lowercase SHA-256 digest."""
    digest = str(value)
    if not SHA256_RE.fullmatch(digest):
        raise RuntimeError(f"{field} is not a lowercase SHA-256")
    return digest


def load_object(path: Path) -> dict[str, Any]:
    """Load one JSON object without following symlinked files."""
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"unsafe or missing state file: {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path.name} is not a JSON object")
    return value


def verify_configuration(value: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Verify the closed configuration shape and exact content pins."""
    verify_schema("wayback-replay-configuration.schema.json", value)
    fields = {
        "schema",
        "selection_sha256",
        "members",
        "replay_policy_sha256",
        "producer",
        "producer_version",
        "parser_version",
        "jitter_seed",
        "policy",
    }
    if set(value) != fields or value.get("schema") != "fyi-archive.wayback-replay-configuration.v1":
        raise RuntimeError("configuration shape or schema is invalid")
    members = value.get("members")
    if not isinstance(members, list) or not members:
        raise RuntimeError("configuration has no ordered members")
    member_ids: set[str] = set()
    for member in members:
        if not isinstance(member, dict) or set(member) != {
            "member_id",
            "canonical_url",
            "capture_timestamp",
        }:
            raise RuntimeError("configuration member shape is invalid")
        member_id = str(member["member_id"])
        if not member_id or member_id in member_ids:
            raise RuntimeError("configuration member IDs are empty or repeated")
        member_ids.add(member_id)
        url = urlsplit(str(member["canonical_url"]))
        if (
            url.scheme != "https"
            or not url.hostname
            or url.hostname.lower() != url.hostname
            or url.username is not None
            or url.password is not None
            or url.fragment
            or url.port not in (None, 443)
        ):
            raise RuntimeError("configuration member URL is invalid")
        captured = datetime.fromisoformat(str(member["capture_timestamp"]))
        if captured.tzinfo is None:
            raise RuntimeError("configuration capture timestamp has no timezone")
    if content_hash(members) != require_hash(value["selection_sha256"], "selection_sha256"):
        raise RuntimeError("selection digest does not match ordered membership")
    policy = value.get("policy")
    if not isinstance(policy, dict):
        raise RuntimeError("configuration policy is invalid")
    expected_policy = {
        "floor_seconds",
        "ceiling_seconds",
        "backoff_multiplier",
        "jitter_fraction",
        "decay_factor",
        "circuit_seconds",
        "circuit_consecutive_failures",
        "failure_ratio",
        "window_size",
        "minimum_window",
        "archive_hosts",
        "allowed_content_types",
        "max_payload_bytes",
    }
    if set(policy) != expected_policy:
        raise RuntimeError("configuration policy shape is invalid")
    numbers = {
        field: policy.get(field)
        for field in (
            "floor_seconds",
            "ceiling_seconds",
            "backoff_multiplier",
            "jitter_fraction",
            "decay_factor",
            "circuit_seconds",
            "failure_ratio",
        )
    }
    if any(
        not isinstance(number, (int, float)) or isinstance(number, bool)
        for number in numbers.values()
    ):
        raise RuntimeError("configuration policy numeric field is invalid")
    if numbers["floor_seconds"] <= 0 or numbers["ceiling_seconds"] <= 0:
        raise RuntimeError("configuration policy pacing must be positive")
    if numbers["floor_seconds"] > numbers["ceiling_seconds"]:
        raise RuntimeError("configuration policy floor exceeds ceiling")
    if numbers["backoff_multiplier"] < 1:
        raise RuntimeError("configuration policy backoff is invalid")
    if numbers["circuit_seconds"] < 0:
        raise RuntimeError("configuration policy circuit duration is invalid")
    if policy["minimum_window"] > policy["window_size"]:
        raise RuntimeError("configuration policy windows are inconsistent")
    if content_hash(policy) != require_hash(value["replay_policy_sha256"], "policy digest"):
        raise RuntimeError("policy digest does not match")
    if not all(
        str(value.get(field, "")).strip()
        for field in ("producer", "producer_version", "parser_version")
    ):
        raise RuntimeError("configuration producer or parser binding is empty")
    if not isinstance(value.get("jitter_seed"), int):
        raise RuntimeError("configuration jitter seed is invalid")
    return content_hash(value), members


def verify_journal(
    root: Path, members: list[dict[str, Any]], policy: dict[str, Any]
) -> tuple[int, str | None, list[dict[str, Any]]]:
    """Verify journal chain, identities, attempt ordering, and content objects."""
    path = root / "attempts.jsonl"
    if not path.exists():
        return 0, None, []
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("attempt journal is unsafe")
    identities = {str(member["member_id"]): member for member in members}
    previous: str | None = None
    entries: list[dict[str, Any]] = []
    occurrences: set[str] = set()
    attempts: dict[str, int] = {}
    for sequence, raw in enumerate(path.read_bytes().splitlines()):
        value = json.loads(raw)
        verify_schema("wayback-replay-attempt.schema.json", value)
        supplied = require_hash(value.pop("entry_sha256", ""), "entry_sha256")
        expected_fields = {
            "schema",
            "occurrence_id",
            "member_id",
            "canonical_url",
            "capture_timestamp",
            "attempt_number",
            "observed_at",
            "outcome_code",
            "retry_disposition",
            "object_sha256",
            "final_url",
            "content_type",
            "payload_bytes",
            "pacing",
            "sequence",
            "previous_entry_sha256",
        }
        if (
            set(value) != expected_fields
            or value.get("schema") != "fyi-archive.wayback-replay-attempt.v1"
        ):
            raise RuntimeError("attempt journal entry shape is invalid")
        if (
            value.get("sequence") != sequence
            or value.get("previous_entry_sha256") != previous
            or content_hash(value) != supplied
        ):
            raise RuntimeError("attempt journal chain is invalid")
        member_id = str(value.get("member_id", ""))
        member = identities.get(member_id)
        if (
            member is None
            or value.get("canonical_url") != member["canonical_url"]
            or (value.get("capture_timestamp") != member["capture_timestamp"])
        ):
            raise RuntimeError("attempt journal identity is outside the selection")
        occurrence = str(value.get("occurrence_id", ""))
        if not occurrence or occurrence in occurrences:
            raise RuntimeError("attempt occurrence IDs are empty or repeated")
        occurrences.add(occurrence)
        attempt = int(value.get("attempt_number", 0))
        if attempt <= attempts.get(member_id, 0):
            raise RuntimeError("attempt numbers do not increase")
        attempts[member_id] = attempt
        object_digest = value.get("object_sha256")
        disposition = value.get("retry_disposition")
        if disposition not in {"complete", "retryable", "terminal"}:
            raise RuntimeError("attempt retry disposition is invalid")
        if (disposition == "complete") != (object_digest is not None):
            raise RuntimeError("attempt object and disposition are inconsistent")
        if object_digest is not None:
            digest = require_hash(object_digest, "object_sha256")
            object_path = root / "objects" / "sha256" / digest[:2] / digest
            if object_path.is_symlink() or not object_path.is_file():
                raise RuntimeError("referenced content object is unsafe or missing")
            payload = object_path.read_bytes()
            if hashlib.sha256(payload).hexdigest() != digest:
                raise RuntimeError("referenced content object is corrupt")
            if value.get("payload_bytes") != len(payload):
                raise RuntimeError("attempt payload size differs from content object")
            final = urlsplit(str(value.get("final_url") or ""))
            try:
                final_port = final.port
            except ValueError as error:
                raise RuntimeError("attempt final archive URL is invalid") from error
            if (
                final.scheme != "https"
                or not final.hostname
                or final.username is not None
                or final.password is not None
                or final.fragment
                or final_port not in (None, 443)
                or final.hostname.lower() not in set(policy["archive_hosts"])
            ):
                raise RuntimeError("attempt escaped the configured archive host boundary")
            media_type = str(value.get("content_type") or "").split(";", 1)[0].strip().lower()
            if media_type not in set(policy["allowed_content_types"]):
                raise RuntimeError("attempt content type is not allowed")
            if len(payload) > int(policy["max_payload_bytes"]):
                raise RuntimeError("attempt payload exceeds configured maximum")
        elif any(
            value.get(field) is not None for field in ("final_url", "content_type", "payload_bytes")
        ):
            raise RuntimeError("non-complete attempt contains response metadata")
        value["entry_sha256"] = supplied
        entries.append(value)
        previous = supplied
    return len(entries), previous, entries


def verify(root: Path) -> dict[str, Any]:
    """Independently verify an entire replay-state directory."""
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("replay root is unsafe or missing")
    configuration = load_object(root / "configuration.json")
    configuration_hash, members = verify_configuration(configuration)
    checkpoint = load_object(root / "checkpoint.json")
    verify_schema("wayback-replay-checkpoint.schema.json", checkpoint)
    supplied_checkpoint = require_hash(checkpoint.pop("checkpoint_sha256", ""), "checkpoint_sha256")
    expected_checkpoint_fields = {
        "schema",
        "configuration_sha256",
        "selection_sha256",
        "replay_policy_sha256",
        "producer",
        "producer_version",
        "parser_version",
        "jitter_seed",
        "member_states",
        "counts",
        "journal_entry_count",
        "journal_tail_sha256",
        "pacing",
    }
    if (
        set(checkpoint) != expected_checkpoint_fields
        or checkpoint.get("schema") != "fyi-archive.wayback-replay-checkpoint.v1"
    ):
        raise RuntimeError("checkpoint shape or schema is invalid")
    if content_hash(checkpoint) != supplied_checkpoint:
        raise RuntimeError("checkpoint self-pin does not match")
    bindings = {
        "configuration_sha256": configuration_hash,
        "selection_sha256": configuration["selection_sha256"],
        "replay_policy_sha256": configuration["replay_policy_sha256"],
        "producer": configuration["producer"],
        "producer_version": configuration["producer_version"],
        "parser_version": configuration["parser_version"],
        "jitter_seed": configuration["jitter_seed"],
    }
    for field, expected in bindings.items():
        if checkpoint.get(field) != expected:
            raise RuntimeError(f"checkpoint {field} does not match configuration")
    states = checkpoint.get("member_states")
    expected_order = [str(member["member_id"]) for member in members]
    if not isinstance(states, dict) or list(states) != expected_order:
        raise RuntimeError("checkpoint population identity or order changed")
    if any(state not in ALLOWED_STATES for state in states.values()):
        raise RuntimeError("checkpoint member state is invalid")
    counts = checkpoint.get("counts")
    expected_count_fields = {
        "population",
        "pending",
        "complete",
        "retryable",
        "terminal",
        "replacement_candidates",
    }
    if (
        not isinstance(counts, dict)
        or set(counts) != expected_count_fields
        or int(counts.get("population", -1)) != len(members)
    ):
        raise RuntimeError("checkpoint population count is invalid")
    actual = {state: sum(value == state for value in states.values()) for state in ALLOWED_STATES}
    if any(int(counts.get(state, -1)) != actual[state] for state in ALLOWED_STATES):
        raise RuntimeError("checkpoint state counts do not match")
    if sum(actual.values()) != len(members):
        raise RuntimeError("population conservation failed")
    journal_count, journal_tail, entries = verify_journal(root, members, configuration["policy"])
    if (
        checkpoint.get("journal_entry_count") != journal_count
        or checkpoint.get("journal_tail_sha256") != journal_tail
    ):
        raise RuntimeError("checkpoint does not match the attempt journal")
    derived_states = dict.fromkeys(expected_order, "pending")
    for entry in entries:
        derived_states[str(entry["member_id"])] = str(entry["retry_disposition"])
    if states != derived_states:
        raise RuntimeError("checkpoint member states differ from attempt journal")
    if entries and checkpoint.get("pacing") != entries[-1].get("pacing"):
        raise RuntimeError("checkpoint pacing differs from attempt journal")
    return {
        "schema": "fyi-archive.wayback-replay-verification.v1",
        "valid": True,
        "configuration_sha256": configuration_hash,
        "checkpoint_sha256": supplied_checkpoint,
        "selection_sha256": configuration["selection_sha256"],
        "population": len(members),
        "journal_entries": len(entries),
        "counts": counts,
    }


def main() -> int:
    """Run the standalone verifier CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    try:
        report = verify(arguments.root)
    except (OSError, TypeError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"invalid: {error}", file=sys.stderr)
        return 1
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output is None:
        print(rendered, end="")
    else:
        arguments.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
