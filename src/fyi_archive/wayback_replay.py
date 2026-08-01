"""Transport-independent state machine for bounded Wayback replay.

The module intentionally contains no HTTP client.  A network-owning caller such
as ``fyi-cli`` supplies immutable :class:`ReplayObservation` values; this
package persists and verifies the resulting acquisition state.
"""

from __future__ import annotations

import email.utils
import hashlib
import json
import math
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol, cast
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from fyi_archive.wayback_cdx_approvals import (
    APPROVED_APPROVAL_REGISTRY_SHA256,
    CdxApprovalError,
    load_approved_cdx_evidence,
    query_scope_allows_url,
    registered_cdx_approval,
)

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
TERMINAL_STATUS = frozenset({404, 410})
RETRYABLE_TRANSPORT = frozenset({"timeout", "connection"})
TERMINAL_CODES = frozenset({
    "redirect_escape",
    "payload_too_large",
    "scope_violation",
    "integrity_mismatch",
    "unsupported_content_type",
    "malformed_content",
})
PACKAGE_SCHEMA_DIRECTORY = Path(__file__).parent / "schemas"
SCHEMA_DIRECTORY = (
    PACKAGE_SCHEMA_DIRECTORY
    if PACKAGE_SCHEMA_DIRECTORY.is_dir()
    else Path(__file__).parents[2] / "schemas"
)
BOUNDARY_REGISTRY_PATH = Path(__file__).parent / "data" / "wayback_replay_boundary_registry.json"
APPROVED_BOUNDARY_REGISTRY_SHA256 = (
    "71045c0446973cc28b12e41eb2201e6c8c896f53b0b59a51ba2f8b6063d3a7ea"
)


class ReplayStateError(RuntimeError):
    """Raised when replay state would fail open or lose integrity."""


class RandomSource(Protocol):
    """Small injected random boundary used by deterministic pacing."""

    def random(self) -> float:
        """Return a value in the half-open interval [0, 1)."""


@dataclass(frozen=True)
class ReplayObservation:
    """One immutable result supplied by the network-owning transport."""

    kind: Literal["success", "http", "transport", "terminal"]
    status_code: int | None = None
    transport_code: str | None = None
    terminal_code: str | None = None
    response_bytes: bytes | None = None
    response_sha256: str | None = None
    retry_after: str | None = None
    final_url: str | None = None
    content_type: str | None = None


class ObservationTransport(Protocol):
    """Injected boundary implemented by the network-owning fyi-cli layer."""

    def observe(self, member: Mapping[str, object]) -> ReplayObservation:
        """Return one immutable observation for an authorized member."""
        ...


@dataclass(frozen=True)
class Outcome:
    """Stable classification of an observation."""

    code: str
    retry_disposition: Literal["retryable", "terminal", "complete"]


@dataclass(frozen=True)
class PacingDecision:
    """Deterministic pacing and circuit state after one observation."""

    delay_seconds: float
    consecutive_failures: int
    window: tuple[bool, ...]
    circuit_open_until: str | None


def canonical_json(value: object) -> bytes:
    """Return the single canonical JSON representation used for all hashes."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of bytes."""
    return hashlib.sha256(value).hexdigest()


def content_hash(value: object) -> str:
    """Hash one JSON-compatible object canonically."""
    return sha256_bytes(canonical_json(value))


def _validate_schema(filename: str, value: object) -> None:
    """Enforce a published replay schema at the untrusted-data boundary."""
    schema = json.loads((SCHEMA_DIRECTORY / filename).read_text(encoding="utf-8"))
    try:
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
    except ValidationError as error:
        raise ReplayStateError(f"{filename} validation failed: {error.message}") from error


def _require_sha256(value: object, field: str) -> str:
    digest = str(value)
    if not SHA256_RE.fullmatch(digest):
        raise ReplayStateError(f"{field} must be a lowercase SHA-256")
    return digest


def _number(value: object, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ReplayStateError(f"{field} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ReplayStateError(f"{field} must be finite")
    return result


def _integer(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ReplayStateError(f"{field} must be an integer")
    return value


def _require_plain_directory(path: Path, *, create: bool = False) -> None:
    if create:
        path.mkdir(parents=True, exist_ok=True)
    current = path
    while current != current.parent:
        if current.exists() and current.is_symlink():
            raise ReplayStateError(f"symlink is not allowed in state path: {current}")
        current = current.parent
    if not path.is_dir():
        raise ReplayStateError(f"state path is not a directory: {path}")


def _atomic_write(path: Path, payload: bytes) -> None:
    _require_plain_directory(path.parent, create=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        # POSIX permits opening and fsyncing a directory to make the rename
        # durable. Windows rejects opening a directory through ``os.open``;
        # ``Path.replace`` remains atomic there, so skip only the unsupported
        # directory flush while retaining the file fsync above.
        if os.name != "nt":
            directory_descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def store_object(root: Path, payload: bytes, *, expected_sha256: str | None = None) -> str:
    """Store bytes in a protected SHA-256 content-addressed object directory."""
    digest = sha256_bytes(payload)
    if expected_sha256 is not None and digest != _require_sha256(
        expected_sha256, "expected_sha256"
    ):
        raise ReplayStateError("object payload does not match expected SHA-256")
    objects = root / "objects" / "sha256"
    _require_plain_directory(objects, create=True)
    destination = objects / digest[:2] / digest
    _require_plain_directory(destination.parent, create=True)
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() or not destination.is_file():
            raise ReplayStateError("existing object is not a regular file")
        if sha256_bytes(destination.read_bytes()) != digest:
            raise ReplayStateError("content-addressed object collision or corruption")
        return digest
    _atomic_write(destination, payload)
    if destination.is_symlink() or sha256_bytes(destination.read_bytes()) != digest:
        raise ReplayStateError("stored object failed integrity verification")
    return digest


def object_path(root: Path, digest: str) -> Path:
    """Resolve a validated object digest without accepting arbitrary paths."""
    valid = _require_sha256(digest, "object_sha256")
    return root / "objects" / "sha256" / valid[:2] / valid


def validate_canonical_url(value: str) -> str:
    """Require one absolute, fragment-free canonical HTTPS URL."""
    parsed = urlsplit(value)
    has_userinfo = parsed.username is not None or parsed.password is not None
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or has_userinfo
        or parsed.fragment
        or parsed.port not in {None, 443}
    ):
        raise ReplayStateError("URL is not an absolute canonical HTTPS URL")
    if parsed.hostname.lower() != parsed.hostname or "/../" in parsed.path or "/./" in parsed.path:
        raise ReplayStateError("URL is not canonical")
    return value


def _validate_member(member: Mapping[str, object]) -> None:
    if not str(member.get("member_id", "")).strip():
        raise ReplayStateError("selection member_id is required")
    validate_canonical_url(str(member.get("canonical_url", "")))
    timestamp = str(member.get("capture_timestamp", ""))
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError as error:
        raise ReplayStateError("capture_timestamp must be an ISO date-time") from error
    if parsed.tzinfo is None:
        raise ReplayStateError("capture_timestamp must include a timezone")


def _require_datetime(value: object, field: str) -> str:
    rendered = str(value)
    try:
        parsed = datetime.fromisoformat(rendered)
    except ValueError as error:
        raise ReplayStateError(f"{field} must be an ISO date-time") from error
    if parsed.tzinfo is None:
        raise ReplayStateError(f"{field} must include a timezone")
    return rendered


def _load_boundary_profile(registry_sha256: object, profile_id: object) -> dict[str, Any]:
    """Resolve a policy boundary from the package-pinned external registry."""
    if BOUNDARY_REGISTRY_PATH.is_symlink() or not BOUNDARY_REGISTRY_PATH.is_file():
        raise ReplayStateError("Wayback boundary registry is missing or unsafe")
    try:
        raw_registry = BOUNDARY_REGISTRY_PATH.read_bytes()
        registry = json.loads(raw_registry.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReplayStateError("Wayback boundary registry is unreadable") from error
    _validate_schema("wayback-replay-boundary-registry.schema.json", registry)
    actual = sha256_bytes(raw_registry)
    supplied = _require_sha256(registry_sha256, "boundary_registry_sha256")
    if actual != APPROVED_BOUNDARY_REGISTRY_SHA256 or supplied != actual:
        raise ReplayStateError("Wayback boundary registry pin does not match")
    profiles = cast("list[dict[str, Any]]", registry["profiles"])
    matches = [profile for profile in profiles if profile["profile_id"] == profile_id]
    if len(matches) != 1:
        raise ReplayStateError("Wayback boundary registry profile is not approved")
    return matches[0]


def validate_configuration(configuration: Mapping[str, object]) -> dict[str, Any]:
    """Validate and normalize an immutable replay configuration."""
    _validate_schema("wayback-replay-configuration.schema.json", dict(configuration))
    required = {
        "schema",
        "selection_sha256",
        "members",
        "replay_policy_sha256",
        "boundary_registry_sha256",
        "boundary_profile_id",
        "producer",
        "producer_version",
        "parser_version",
        "jitter_seed",
        "policy",
    }
    if set(configuration) != required:
        raise ReplayStateError("configuration fields do not match the replay contract")
    if configuration["schema"] != "fyi-archive.wayback-replay-configuration.v1":
        raise ReplayStateError("unsupported replay configuration schema")
    _require_sha256(configuration["selection_sha256"], "selection_sha256")
    _require_sha256(configuration["replay_policy_sha256"], "replay_policy_sha256")
    boundary = _load_boundary_profile(
        configuration["boundary_registry_sha256"], configuration["boundary_profile_id"]
    )
    raw_members = configuration["members"]
    if not isinstance(raw_members, list) or not raw_members:
        raise ReplayStateError("members must be a non-empty ordered array")
    members = cast("list[dict[str, object]]", raw_members)
    ids: set[str] = set()
    for member in members:
        if not isinstance(member, dict):
            raise ReplayStateError("every selection member must be an object")
        _validate_member(member)
        member_id = str(member["member_id"])
        if member_id in ids:
            raise ReplayStateError("selection member IDs must be unique")
        ids.add(member_id)
    computed_selection = content_hash(members)
    if computed_selection != configuration["selection_sha256"]:
        raise ReplayStateError("selection SHA-256 does not match ordered membership")
    policy = configuration["policy"]
    if not isinstance(policy, dict):
        raise ReplayStateError("policy must be an object")
    numeric_fields = (
        "floor_seconds",
        "ceiling_seconds",
        "backoff_multiplier",
        "jitter_fraction",
        "decay_factor",
        "circuit_seconds",
        "failure_ratio",
    )
    integer_fields = ("circuit_consecutive_failures", "window_size", "minimum_window")
    for field in numeric_fields:
        _number(policy.get(field), f"policy {field}")
    for field in integer_fields:
        if _integer(policy.get(field), f"policy {field}") <= 0:
            raise ReplayStateError(f"policy {field} must be a positive integer")
    if not 0 <= _number(policy.get("jitter_fraction"), "policy jitter_fraction") <= 1:
        raise ReplayStateError("policy jitter_fraction must be between zero and one")
    if not 0 <= _number(policy.get("failure_ratio"), "policy failure_ratio") <= 1:
        raise ReplayStateError("policy failure_ratio must be between zero and one")
    if not 0 < _number(policy.get("decay_factor"), "policy decay_factor") <= 1:
        raise ReplayStateError("policy decay_factor must be in (0, 1]")
    if _number(policy.get("floor_seconds"), "policy floor_seconds") > _number(
        policy.get("ceiling_seconds"), "policy ceiling_seconds"
    ):
        raise ReplayStateError("policy floor exceeds ceiling")
    if _number(policy.get("floor_seconds"), "policy floor_seconds") <= 0:
        raise ReplayStateError("policy floor_seconds must be positive")
    if _number(policy.get("ceiling_seconds"), "policy ceiling_seconds") <= 0:
        raise ReplayStateError("policy ceiling_seconds must be positive")
    if _number(policy.get("backoff_multiplier"), "policy backoff_multiplier") < 1:
        raise ReplayStateError("policy backoff_multiplier must be at least one")
    if _number(policy.get("circuit_seconds"), "policy circuit_seconds") < 0:
        raise ReplayStateError("policy circuit_seconds must be nonnegative")
    if _integer(policy.get("minimum_window"), "policy minimum_window") > _integer(
        policy.get("window_size"), "policy window_size"
    ):
        raise ReplayStateError("policy minimum_window exceeds window_size")
    if content_hash(policy) != configuration["replay_policy_sha256"]:
        raise ReplayStateError("replay policy SHA-256 does not match policy")
    for field in ("archive_hosts", "allowed_content_types", "max_payload_bytes"):
        if policy.get(field) != boundary[field]:
            raise ReplayStateError(f"policy {field} exceeds the external boundary registry")
    for field in ("producer", "producer_version", "parser_version"):
        if not str(configuration[field]).strip():
            raise ReplayStateError(f"{field} is required")
    if not isinstance(configuration["jitter_seed"], int):
        raise ReplayStateError("jitter_seed must be an integer")
    return json.loads(canonical_json(configuration))


def initial_checkpoint(configuration: Mapping[str, object]) -> dict[str, Any]:
    """Create the first configuration-bound replay checkpoint."""
    normalized = validate_configuration(configuration)
    members = cast("list[dict[str, object]]", normalized["members"])
    states = {str(member["member_id"]): "pending" for member in members}
    checkpoint: dict[str, Any] = {
        "schema": "fyi-archive.wayback-replay-checkpoint.v1",
        "configuration_sha256": content_hash(normalized),
        "selection_sha256": normalized["selection_sha256"],
        "replay_policy_sha256": normalized["replay_policy_sha256"],
        "boundary_registry_sha256": normalized["boundary_registry_sha256"],
        "boundary_profile_id": normalized["boundary_profile_id"],
        "producer": normalized["producer"],
        "producer_version": normalized["producer_version"],
        "parser_version": normalized["parser_version"],
        "jitter_seed": normalized["jitter_seed"],
        "member_states": states,
        "counts": {
            "population": len(members),
            "pending": len(members),
            "complete": 0,
            "retryable": 0,
            "terminal": 0,
            "replacement_candidates": 0,
        },
        "journal_entry_count": 0,
        "journal_tail_sha256": None,
        "pacing": {
            "delay_seconds": _number(
                cast("dict[str, object]", normalized["policy"])["floor_seconds"],
                "policy floor_seconds",
            ),
            "consecutive_failures": 0,
            "window": [],
            "circuit_open_until": None,
        },
    }
    checkpoint["checkpoint_sha256"] = content_hash(checkpoint)
    return checkpoint


def verify_checkpoint(
    checkpoint: Mapping[str, object], configuration: Mapping[str, object]
) -> dict[str, Any]:
    """Verify configuration binding, self-pin, state vocabulary, and conservation."""
    normalized = validate_configuration(configuration)
    _validate_schema("wayback-replay-checkpoint.schema.json", dict(checkpoint))
    value = dict(checkpoint)
    supplied_pin = _require_sha256(value.pop("checkpoint_sha256", ""), "checkpoint_sha256")
    if content_hash(value) != supplied_pin:
        raise ReplayStateError("checkpoint self-pin does not match")
    exact_bindings = {
        "configuration_sha256": content_hash(normalized),
        "selection_sha256": normalized["selection_sha256"],
        "replay_policy_sha256": normalized["replay_policy_sha256"],
        "boundary_registry_sha256": normalized["boundary_registry_sha256"],
        "boundary_profile_id": normalized["boundary_profile_id"],
        "producer": normalized["producer"],
        "producer_version": normalized["producer_version"],
        "parser_version": normalized["parser_version"],
        "jitter_seed": normalized["jitter_seed"],
    }
    for field, expected in exact_bindings.items():
        if value.get(field) != expected:
            raise ReplayStateError(f"checkpoint {field} does not match configuration")
    member_ids = [str(member["member_id"]) for member in normalized["members"]]
    states = value.get("member_states")
    if not isinstance(states, dict) or list(states) != member_ids:
        raise ReplayStateError("checkpoint membership or ordering changed")
    allowed_states = {"pending", "complete", "retryable", "terminal"}
    if any(state not in allowed_states for state in states.values()):
        raise ReplayStateError("checkpoint has an invalid member state")
    counts = value.get("counts")
    if not isinstance(counts, dict):
        raise ReplayStateError("checkpoint counts are missing")
    actual = {state: sum(item == state for item in states.values()) for state in allowed_states}
    if _integer(counts.get("population", -1), "counts population") != len(member_ids):
        raise ReplayStateError("checkpoint population count changed")
    if any(
        _integer(counts.get(state, -1), f"counts {state}") != actual[state]
        for state in allowed_states
    ):
        raise ReplayStateError("checkpoint state counts do not match membership")
    if sum(actual.values()) != len(member_ids):
        raise ReplayStateError("checkpoint population conservation failed")
    if _integer(counts.get("replacement_candidates", -1), "counts replacement_candidates") < 0:
        raise ReplayStateError("replacement candidate count is invalid")
    return dict(checkpoint)


def _validate_success_boundary(
    observation: ReplayObservation, policy: Mapping[str, object]
) -> None:
    """Reject successful transport observations outside the configured archive boundary."""
    if observation.response_bytes is None:
        raise ReplayStateError("successful observation has no response bytes")
    final_url = str(observation.final_url or "")
    try:
        parsed = urlsplit(final_url)
        port = parsed.port
    except ValueError as error:
        raise ReplayStateError("successful observation has an invalid final archive URL") from error
    has_userinfo = parsed.username is not None or parsed.password is not None
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or has_userinfo
        or parsed.fragment
        or port not in {None, 443}
    ):
        raise ReplayStateError("successful observation has an invalid final archive URL")
    allowed_hosts = cast("Sequence[object]", policy["archive_hosts"])
    if parsed.hostname.lower() not in {str(host) for host in allowed_hosts}:
        raise ReplayStateError(
            "successful observation escaped the configured archive host boundary"
        )
    media_type = str(observation.content_type or "").split(";", 1)[0].strip().lower()
    allowed_types = {
        str(item) for item in cast("Sequence[object]", policy["allowed_content_types"])
    }
    if media_type not in allowed_types:
        raise ReplayStateError("successful observation content type is not allowed")
    maximum = _integer(policy["max_payload_bytes"], "policy max_payload_bytes")
    if len(observation.response_bytes) > maximum:
        raise ReplayStateError("successful observation payload exceeds configured maximum")


def classify_observation(
    observation: ReplayObservation, *, policy: Mapping[str, object] | None = None
) -> Outcome:
    """Classify a transport observation into one stable retry disposition."""
    if observation.kind == "success":
        if policy is None:
            raise ReplayStateError("successful observation requires a validated replay policy")
        _validate_success_boundary(observation, policy)
        payload = cast("bytes", observation.response_bytes)
        if observation.response_sha256 is not None and sha256_bytes(payload) != _require_sha256(
            observation.response_sha256, "response_sha256"
        ):
            return Outcome("integrity_mismatch", "terminal")
        return Outcome("success", "complete")
    if observation.kind == "http":
        if observation.status_code in RETRYABLE_STATUS:
            return Outcome(f"http_{observation.status_code}", "retryable")
        if observation.status_code in TERMINAL_STATUS:
            return Outcome(f"http_{observation.status_code}", "terminal")
        raise ReplayStateError("unregistered HTTP status outcome")
    if observation.kind == "transport":
        if observation.transport_code in RETRYABLE_TRANSPORT:
            return Outcome(str(observation.transport_code), "retryable")
        raise ReplayStateError("unregistered transport outcome")
    if observation.kind == "terminal" and observation.terminal_code in TERMINAL_CODES:
        return Outcome(str(observation.terminal_code), "terminal")
    raise ReplayStateError("unregistered observation outcome")


def parse_retry_after(value: str | None, *, now: datetime, ceiling_seconds: float) -> float | None:
    """Parse Retry-After seconds or HTTP-date and cap it to the policy ceiling."""
    if value is None:
        return None
    stripped = value.strip()
    if stripped.isdigit():
        return min(float(stripped), ceiling_seconds)
    try:
        parsed = email.utils.parsedate_to_datetime(stripped)
    except (TypeError, ValueError):
        return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    reference = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
    return min(max(0.0, (parsed - reference).total_seconds()), ceiling_seconds)


def next_pacing(
    *,
    previous: Mapping[str, object],
    outcome: Outcome,
    policy: Mapping[str, object],
    now: datetime,
    rng: RandomSource,
    retry_after: str | None = None,
) -> PacingDecision:
    """Compute deterministic adaptive pacing using injected time and randomness."""
    floor = _number(policy["floor_seconds"], "policy floor_seconds")
    ceiling = _number(policy["ceiling_seconds"], "policy ceiling_seconds")
    previous_delay = _number(previous["delay_seconds"], "pacing delay_seconds")
    failures = _integer(previous["consecutive_failures"], "pacing consecutive_failures")
    window = tuple(bool(item) for item in cast("Sequence[object]", previous["window"]))
    failed = outcome.retry_disposition == "retryable"
    if failed:
        failures += 1
        base = max(
            floor,
            previous_delay * _number(policy["backoff_multiplier"], "policy backoff_multiplier"),
        )
        explicit = parse_retry_after(retry_after, now=now, ceiling_seconds=ceiling)
        if explicit is not None:
            base = max(base, explicit)
        jitter_span = min(base, ceiling) * _number(
            policy["jitter_fraction"], "policy jitter_fraction"
        )
        delay = min(ceiling, base + (rng.random() * jitter_span))
    elif outcome.retry_disposition == "complete":
        failures = 0
        delay = max(
            floor,
            previous_delay * _number(policy["decay_factor"], "policy decay_factor"),
        )
    else:
        failures = 0
        delay = max(floor, previous_delay)
    window_size = _integer(policy["window_size"], "policy window_size")
    updated_window = (*window, failed)[-window_size:]
    enough_window = len(updated_window) >= _integer(
        policy["minimum_window"], "policy minimum_window"
    )
    ratio = sum(updated_window) / len(updated_window) if updated_window else 0.0
    opens = failed and (
        failures
        >= _integer(policy["circuit_consecutive_failures"], "policy circuit_consecutive_failures")
        or (enough_window and ratio >= _number(policy["failure_ratio"], "policy failure_ratio"))
    )
    circuit_open_until = None
    if opens:
        seconds = _number(policy["circuit_seconds"], "policy circuit_seconds")
        circuit_open_until = (
            datetime
            .fromtimestamp(now.timestamp() + seconds, tz=UTC)
            .isoformat()
            .replace("+00:00", "Z")
        )
    return PacingDecision(delay, failures, updated_window, circuit_open_until)


def append_attempt(journal_path: Path, entry: Mapping[str, object]) -> dict[str, Any]:
    """Append one canonical, hash-chained journal entry and fsync it."""
    _require_plain_directory(journal_path.parent, create=True)
    if journal_path.exists() and (journal_path.is_symlink() or not journal_path.is_file()):
        raise ReplayStateError("attempt journal is not a regular file")
    previous_hash: str | None = None
    sequence = 0
    if journal_path.exists():
        lines = journal_path.read_bytes().splitlines()
        if lines:
            previous = json.loads(lines[-1])
            previous_hash = _require_sha256(previous.get("entry_sha256"), "entry_sha256")
            sequence = int(previous["sequence"]) + 1
    value = dict(entry)
    forbidden = {"sequence", "previous_entry_sha256", "entry_sha256"}
    if forbidden.intersection(value):
        raise ReplayStateError("journal caller may not supply chain fields")
    value["sequence"] = sequence
    value["previous_entry_sha256"] = previous_hash
    value["entry_sha256"] = content_hash(value)
    encoded = canonical_json(value) + b"\n"
    with journal_path.open("ab") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    return value


def verify_journal(journal_path: Path) -> tuple[int, str | None, list[dict[str, Any]]]:
    """Verify the complete append-only chain and return its count and tail."""
    if not journal_path.exists():
        return 0, None, []
    if journal_path.is_symlink() or not journal_path.is_file():
        raise ReplayStateError("attempt journal is not a regular file")
    entries: list[dict[str, Any]] = []
    previous_hash: str | None = None
    for sequence, line in enumerate(journal_path.read_bytes().splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ReplayStateError("attempt journal contains malformed JSON") from error
        _validate_schema("wayback-replay-attempt.schema.json", value)
        if value.get("sequence") != sequence or value.get("previous_entry_sha256") != previous_hash:
            raise ReplayStateError("attempt journal sequence or chain is broken")
        supplied = _require_sha256(value.pop("entry_sha256", ""), "entry_sha256")
        if content_hash(value) != supplied:
            raise ReplayStateError("attempt journal entry hash does not match")
        value["entry_sha256"] = supplied
        previous_hash = supplied
        entries.append(value)
    return len(entries), previous_hash, entries


def replacement_candidate(
    *,
    configuration: Mapping[str, object],
    checkpoint: Mapping[str, object],
    member_id: str,
    candidate_url: str,
    capture_timestamp: str,
    source_metadata_path: Path,
    source_metadata_sha256: str,
    source_row_sha256: str,
    retrieval_evidence_path: Path,
    retrieval_evidence_sha256: str,
) -> dict[str, Any]:
    """Create a replacement candidate from one verified, pinned CDX row."""
    normalized = validate_configuration(configuration)
    verified_checkpoint = verify_checkpoint(checkpoint, normalized)
    members = {
        str(member["member_id"]): member
        for member in cast("list[dict[str, object]]", normalized["members"])
    }
    member = members.get(member_id)
    if member is None:
        raise ReplayStateError("replacement candidate member is outside the configured population")
    states = cast("dict[str, str]", verified_checkpoint["member_states"])
    failed_status = states[member_id]
    if failed_status not in {"retryable", "terminal"}:
        raise ReplayStateError("replacement candidate requires a failed member")
    original = validate_canonical_url(str(member["canonical_url"]))
    if validate_canonical_url(candidate_url) != original:
        raise ReplayStateError("replacement candidate URL is not the exact canonical URL")
    expected_artifact_sha256 = _require_sha256(source_metadata_sha256, "source_metadata_sha256")
    expected_row_sha256 = _require_sha256(source_row_sha256, "source_row_sha256")
    try:
        approval, source_metadata, _retrieval_evidence = load_approved_cdx_evidence(
            artifact_path=source_metadata_path,
            artifact_sha256=expected_artifact_sha256,
            retrieval_evidence_path=retrieval_evidence_path,
            retrieval_evidence_sha256=retrieval_evidence_sha256,
        )
    except CdxApprovalError as error:
        raise ReplayStateError(str(error)) from error
    if not query_scope_allows_url(str(approval["query_scope"]), original):
        raise ReplayStateError("replacement candidate URL is outside the approved CDX query scope")
    rows = cast("list[dict[str, Any]]", source_metadata["rows"])
    matching_rows: list[dict[str, Any]] = []
    for raw_row in rows:
        row = dict(raw_row)
        supplied_row_sha256 = _require_sha256(row.pop("row_sha256"), "source row SHA-256")
        if content_hash(row) != supplied_row_sha256:
            raise ReplayStateError("replacement CDX metadata row hash does not match")
        if supplied_row_sha256 == expected_row_sha256:
            matching_rows.append(raw_row)
    if len(matching_rows) != 1:
        raise ReplayStateError("replacement CDX metadata row pin is missing or ambiguous")
    source_row = matching_rows[0]
    candidate_timestamp = _require_datetime(capture_timestamp, "capture_timestamp")
    if (
        source_row["member_id"] != member_id
        or source_row["canonical_url"] != original
        or source_row["capture_timestamp"] != candidate_timestamp
    ):
        raise ReplayStateError("replacement CDX metadata row identity does not match")
    archive_url = urlsplit(validate_canonical_url(str(source_row["archive_url"])))
    timestamp = datetime.fromisoformat(candidate_timestamp).astimezone(UTC)
    cdx_timestamp = timestamp.strftime("%Y%m%d%H%M%S")
    expected_prefix = f"/web/{cdx_timestamp}id_/"
    archived_target = archive_url.path.removeprefix(expected_prefix)
    if archive_url.query:
        archived_target = f"{archived_target}?{archive_url.query}"
    if (
        archive_url.hostname != "web.archive.org"
        or not archive_url.path.startswith(expected_prefix)
        or archived_target != original
    ):
        raise ReplayStateError("replacement CDX metadata archive URL does not match row identity")
    retrieved_at = datetime.fromisoformat(
        _require_datetime(source_metadata["retrieved_at"], "source metadata retrieved_at")
    )
    if timestamp > retrieved_at:
        raise ReplayStateError("replacement capture timestamp is later than metadata retrieval")
    value: dict[str, Any] = {
        "schema": "fyi-archive.wayback-replacement-candidate.v1",
        "configuration_sha256": content_hash(normalized),
        "checkpoint_sha256": verified_checkpoint["checkpoint_sha256"],
        "member_id": member_id,
        "failed_status": failed_status,
        "canonical_url": original,
        "capture_timestamp": candidate_timestamp,
        "approval_id": approval["approval_id"],
        "approval_registry_sha256": APPROVED_APPROVAL_REGISTRY_SHA256,
        "source_metadata_sha256": expected_artifact_sha256,
        "retrieval_evidence_sha256": approval["retrieval_evidence_sha256"],
        "source_row_sha256": expected_row_sha256,
        "endpoint": approval["endpoint"],
        "query_scope": approval["query_scope"],
        "producer_id": approval["producer_id"],
        "retrieved_at": approval["retrieved_at"],
        "status": "pending_replay_approval",
    }
    value["candidate_sha256"] = content_hash(value)
    _validate_schema("wayback-replacement-candidate.schema.json", value)
    return value


def merge_replacement_candidates(
    candidates: Sequence[Mapping[str, object]],
    *,
    configuration: Mapping[str, object],
    checkpoint: Mapping[str, object],
) -> list[dict[str, Any]]:
    """Deduplicate candidates by self-pin and return a deterministic ordering."""
    normalized = validate_configuration(configuration)
    verified_checkpoint = verify_checkpoint(checkpoint, normalized)
    configuration_sha256 = content_hash(normalized)
    checkpoint_sha256 = str(verified_checkpoint["checkpoint_sha256"])
    states = cast("dict[str, str]", verified_checkpoint["member_states"])
    members = {
        str(member["member_id"]): member
        for member in cast("list[dict[str, object]]", normalized["members"])
    }
    unique: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        value = dict(candidate)
        _validate_schema("wayback-replacement-candidate.schema.json", value)
        supplied = _require_sha256(value.pop("candidate_sha256", ""), "candidate_sha256")
        if content_hash(value) != supplied:
            raise ReplayStateError("replacement candidate self-pin does not match")
        if value.get("status") != "pending_replay_approval":
            raise ReplayStateError("replacement candidate is not pending approval")
        if value.get("configuration_sha256") != configuration_sha256:
            raise ReplayStateError("replacement candidate configuration binding does not match")
        if value.get("checkpoint_sha256") != checkpoint_sha256:
            raise ReplayStateError("replacement candidate checkpoint binding does not match")
        member_id = str(value.get("member_id", ""))
        if states.get(member_id) != value.get("failed_status") or states.get(member_id) not in {
            "retryable",
            "terminal",
        }:
            raise ReplayStateError("replacement candidate failed-member binding does not match")
        member = members[member_id]
        if value.get("canonical_url") != member["canonical_url"]:
            raise ReplayStateError("replacement candidate exact URL binding does not match")
        try:
            approval = registered_cdx_approval(
                str(value.get("source_metadata_sha256", "")),
                str(value.get("retrieval_evidence_sha256", "")),
            )
        except CdxApprovalError as error:
            raise ReplayStateError(str(error)) from error
        for field in (
            "approval_id",
            "endpoint",
            "query_scope",
            "producer_id",
            "retrieved_at",
        ):
            if value.get(field) != approval[field]:
                raise ReplayStateError(
                    f"replacement candidate approved provenance differs for {field}"
                )
        if value.get("approval_registry_sha256") != APPROVED_APPROVAL_REGISTRY_SHA256:
            raise ReplayStateError("replacement candidate approval-registry pin does not match")
        if not query_scope_allows_url(str(approval["query_scope"]), str(value["canonical_url"])):
            raise ReplayStateError(
                "replacement candidate URL is outside the approved CDX query scope"
            )
        value["candidate_sha256"] = supplied
        unique[supplied] = value
    return [unique[digest] for digest in sorted(unique)]


def verify_resume_state(
    root: Path,
    configuration: Mapping[str, object],
    checkpoint: Mapping[str, object],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Verify checkpoint, journal, and every referenced content object before resume."""
    normalized = validate_configuration(configuration)
    config_path = root / "configuration.json"
    if config_path.is_symlink() or not config_path.is_file():
        raise ReplayStateError("persisted replay configuration is missing or unsafe")
    try:
        persisted = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReplayStateError("persisted replay configuration is unreadable") from error
    if persisted != normalized:
        raise ReplayStateError("persisted replay configuration does not match resume input")
    verified = verify_checkpoint(checkpoint, normalized)
    count, tail, entries = verify_journal(root / "attempts.jsonl")
    if count != verified["journal_entry_count"] or tail != verified["journal_tail_sha256"]:
        raise ReplayStateError("checkpoint does not match attempt journal")
    configured_members = {
        str(member["member_id"]): member
        for member in cast("list[dict[str, object]]", configuration["members"])
    }
    seen_occurrences: set[str] = set()
    last_attempt: dict[str, int] = {}
    derived_states = dict.fromkeys(configured_members, "pending")
    for entry in entries:
        member_id = str(entry.get("member_id", ""))
        member = configured_members.get(member_id)
        if member is None:
            raise ReplayStateError("journal contains a member outside the selection")
        if (
            entry.get("canonical_url") != member["canonical_url"]
            or entry.get("capture_timestamp") != member["capture_timestamp"]
        ):
            raise ReplayStateError("journal member identity differs from selection")
        occurrence = str(entry.get("occurrence_id", ""))
        if not occurrence or occurrence in seen_occurrences:
            raise ReplayStateError("journal occurrence IDs must be unique")
        seen_occurrences.add(occurrence)
        attempt = int(entry.get("attempt_number", 0))
        if attempt <= last_attempt.get(member_id, 0):
            raise ReplayStateError("journal attempt numbers are not increasing")
        last_attempt[member_id] = attempt
        disposition = str(entry.get("retry_disposition", ""))
        if disposition not in {"complete", "retryable", "terminal"}:
            raise ReplayStateError("journal retry disposition is invalid")
        object_digest = entry.get("object_sha256")
        if (disposition == "complete") != (object_digest is not None):
            raise ReplayStateError("journal object and retry disposition are inconsistent")
        if object_digest is not None:
            path = object_path(root, str(object_digest))
            if path.is_symlink() or not path.is_file():
                raise ReplayStateError("journal content object is missing or unsafe")
            if sha256_bytes(path.read_bytes()) != object_digest:
                raise ReplayStateError("journal content object failed integrity verification")
            payload = path.read_bytes()
            if entry.get("payload_bytes") != len(payload):
                raise ReplayStateError("journal payload size differs from content object")
            _validate_success_boundary(
                ReplayObservation(
                    kind="success",
                    response_bytes=payload,
                    final_url=str(entry.get("final_url") or ""),
                    content_type=str(entry.get("content_type") or ""),
                ),
                cast("dict[str, object]", normalized["policy"]),
            )
        elif any(
            entry.get(field) is not None for field in ("final_url", "content_type", "payload_bytes")
        ):
            raise ReplayStateError("non-complete journal entry contains response metadata")
        derived_states[member_id] = disposition
    if cast("dict[str, str]", verified["member_states"]) != derived_states:
        raise ReplayStateError("checkpoint member states do not match attempt journal")
    if entries and verified["pacing"] != entries[-1].get("pacing"):
        raise ReplayStateError("checkpoint pacing does not match attempt journal")
    return verified, entries


def record_observation(
    *,
    root: Path,
    configuration: Mapping[str, object],
    checkpoint: Mapping[str, object],
    member_id: str,
    occurrence_id: str,
    attempt_number: int,
    observation: ReplayObservation,
    now: datetime,
    rng: RandomSource,
) -> dict[str, Any]:
    """Persist an observation in object, journal, checkpoint commit order."""
    normalized = validate_configuration(configuration)
    current, entries = verify_resume_state(root, normalized, checkpoint)
    states = cast("dict[str, str]", current["member_states"])
    if member_id not in states:
        raise ReplayStateError("attempt member is outside the configured population")
    if states[member_id] in {"complete", "terminal"}:
        raise ReplayStateError("terminal member cannot receive another attempt")
    if attempt_number <= 0 or not occurrence_id.strip():
        raise ReplayStateError("attempt number and occurrence ID are required")
    open_until = cast("dict[str, object]", current["pacing"]).get("circuit_open_until")
    if open_until is not None:
        circuit_until = datetime.fromisoformat(str(open_until))
        reference = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
        if circuit_until > reference:
            raise ReplayStateError("host circuit is open; transport observation is premature")
    if occurrence_id in {str(entry["occurrence_id"]) for entry in entries}:
        raise ReplayStateError("attempt occurrence ID was already used")
    previous_attempts = [
        int(entry["attempt_number"]) for entry in entries if entry["member_id"] == member_id
    ]
    if previous_attempts and attempt_number <= max(previous_attempts):
        raise ReplayStateError("attempt number must increase for the member")
    policy = cast("dict[str, object]", normalized["policy"])
    outcome = classify_observation(observation, policy=policy)
    member = next(item for item in normalized["members"] if str(item["member_id"]) == member_id)
    object_sha256 = None
    if outcome.retry_disposition == "complete":
        object_sha256 = store_object(
            root,
            cast("bytes", observation.response_bytes),
            expected_sha256=observation.response_sha256,
        )
    decision = next_pacing(
        previous=cast("dict[str, object]", current["pacing"]),
        outcome=outcome,
        policy=policy,
        now=now,
        rng=rng,
        retry_after=observation.retry_after,
    )
    journal_entry = append_attempt(
        root / "attempts.jsonl",
        {
            "schema": "fyi-archive.wayback-replay-attempt.v1",
            "occurrence_id": occurrence_id,
            "member_id": member_id,
            "canonical_url": member["canonical_url"],
            "capture_timestamp": member["capture_timestamp"],
            "attempt_number": attempt_number,
            "observed_at": now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "outcome_code": outcome.code,
            "retry_disposition": outcome.retry_disposition,
            "object_sha256": object_sha256,
            "final_url": observation.final_url if object_sha256 is not None else None,
            "content_type": observation.content_type if object_sha256 is not None else None,
            "payload_bytes": (
                len(cast("bytes", observation.response_bytes))
                if object_sha256 is not None
                else None
            ),
            "pacing": {
                "delay_seconds": decision.delay_seconds,
                "consecutive_failures": decision.consecutive_failures,
                "window": list(decision.window),
                "circuit_open_until": decision.circuit_open_until,
            },
        },
    )
    new_state = outcome.retry_disposition
    states[member_id] = new_state
    counts = cast("dict[str, int]", current["counts"])
    for state in ("pending", "complete", "retryable", "terminal"):
        counts[state] = sum(value == state for value in states.values())
    current["journal_entry_count"] = int(journal_entry["sequence"]) + 1
    current["journal_tail_sha256"] = journal_entry["entry_sha256"]
    current["pacing"] = journal_entry["pacing"]
    current.pop("checkpoint_sha256", None)
    current["checkpoint_sha256"] = content_hash(current)
    verified = verify_checkpoint(current, normalized)
    _atomic_write(root / "checkpoint.json", canonical_json(verified) + b"\n")
    return verified


def write_initial_state(root: Path, configuration: Mapping[str, object]) -> dict[str, Any]:
    """Persist a new configuration and its first atomic checkpoint."""
    _require_plain_directory(root, create=True)
    normalized = validate_configuration(configuration)
    config_path = root / "configuration.json"
    checkpoint_path = root / "checkpoint.json"
    if config_path.exists() or checkpoint_path.exists() or (root / "attempts.jsonl").exists():
        raise ReplayStateError("replay state already exists")
    checkpoint = initial_checkpoint(normalized)
    _atomic_write(config_path, canonical_json(normalized) + b"\n")
    _atomic_write(checkpoint_path, canonical_json(checkpoint) + b"\n")
    return checkpoint
