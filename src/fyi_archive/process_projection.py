"""Consume the versioned fyi-cli process-event projection.

The process projection is deliberately separate from the faithful archive
manifest.  It contains public-safe event, case, attachment metadata, and
revision rows suitable for process mining and Dataset Viewer ingestion.
"""

from __future__ import annotations

import hashlib
import json
import operator
from pathlib import Path
from typing import Any

import polars as pl

CONTRACT_VERSION = "1.0.0"
REQUIRED_EVENT_FIELDS = {"event_id", "case_id", "activity"}


def _source_index(row: dict[str, Any]) -> int:
    """Return the source sequence from scalar or fyi-cli structured ordering."""
    value = row.get("source_index", row.get("source_order", 0))
    if isinstance(value, dict):
        value = value.get("event_sequence", value.get("sequence", 0))
    return int(value or 0)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON on line {line_number} of {path}") from error
        if not isinstance(value, dict):
            raise ValueError(f"JSONL line {line_number} must be an object")
        if "case_id" not in value and value.get("logical_request_id"):
            value["case_id"] = value["logical_request_id"]
        rows.append(value)
    return rows


def _read_takedown_ids(path: Path | None) -> set[str]:
    """Read stable case/event IDs that must not enter the derived layer."""
    if path is None or not path.exists():
        return set()
    ids: set[str] = set()
    for row in _read_jsonl(path):
        value = row.get("case_id") or row.get("event_id") or row.get("id")
        if isinstance(value, str) and value:
            ids.add(value)
    return ids


def _validate_events(rows: list[dict[str, Any]]) -> None:
    for index, row in enumerate(rows):
        missing = REQUIRED_EVENT_FIELDS - row.keys()
        if missing:
            raise ValueError(f"event row {index} missing fields: {sorted(missing)}")
        if row.get("contract_version", CONTRACT_VERSION) != CONTRACT_VERSION:
            raise ValueError("unsupported fyi-cli process-event contract version")
        if not isinstance(row["event_id"], str) or not row["event_id"]:
            raise ValueError(f"event row {index} has an invalid event_id")
        if not isinstance(row["case_id"], str) or not row["case_id"]:
            raise ValueError(f"event row {index} has an invalid case_id")


def _sort_events(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("case_id", "")),
            _source_index(row),
            str(row.get("event_id", "")),
        ),
    )


def merge_process_event_logs(paths: list[Path]) -> list[dict[str, Any]]:
    """Merge resumed event-log shards deterministically.

    A logical event revision is immutable once emitted. Duplicate deliveries
    are collapsed, while two different payloads claiming the same logical
    revision fail closed instead of being guessed at.
    """
    merged: dict[tuple[str, int], dict[str, Any]] = {}
    for path in paths:
        for row in _read_jsonl(path):
            logical_id = str(row.get("logical_event_id") or row.get("event_id") or "")
            revision = int(row.get("revision", 1))
            key = (logical_id, revision)
            previous = merged.get(key)
            if previous is None:
                merged[key] = row
            elif previous != row:
                raise ValueError(
                    f"conflicting payloads for logical event revision {logical_id}:{revision}"
                )
    result = _sort_events(list(merged.values()))
    _validate_events(result)
    return result


def _materialize_active_events(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the latest revision of each logical event and apply tombstones."""
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        logical_id = str(row.get("logical_event_id") or row.get("event_id") or "")
        revision = int(row.get("revision", 1))
        previous = latest.get(logical_id)
        if previous is None or (revision, str(row.get("event_id", ""))) > (
            int(previous.get("revision", 1)),
            str(previous.get("event_id", "")),
        ):
            latest[logical_id] = row
    return [row for row in latest.values() if row.get("operation") != "retract"]


def _case_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        grouped.setdefault(event["case_id"], []).append(event)
    result = []
    for case_id, case_events in grouped.items():
        result.append({
            "case_id": case_id,
            "event_count": len(case_events),
            "first_source_index": min(_source_index(event) for event in case_events),
            "last_source_index": max(_source_index(event) for event in case_events),
        })
    return sorted(result, key=operator.itemgetter("case_id"))


def _write_checksums(output_dir: Path, paths: list[Path]) -> None:
    lines = []
    for path in sorted(paths):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(output_dir).as_posix()}")
    (output_dir / "CHECKSUMS.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_process_projection(output_dir: Path) -> None:
    """Verify every file listed by a projection's checksum manifest."""
    checksum_path = output_dir / "CHECKSUMS.sha256"
    if not checksum_path.exists():
        raise ValueError(f"missing checksum manifest: {checksum_path}")
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        path = output_dir / relative
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"checksum mismatch: {relative}")
    coverage_path = output_dir / "coverage.json"
    if coverage_path.exists():
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        for field in ("request_count_reconciles", "attachment_count_reconciles"):
            if coverage.get(field) is False:
                raise ValueError(f"projection coverage does not reconcile: {field}")


def build_process_projection(
    *,
    events_path: Path,
    output_dir: Path,
    manifest_path: Path | None = None,
    attachments_path: Path | None = None,
    takedown_path: Path | None = None,
    source_reconciliation_path: Path | None = None,
    snapshot_revision: str | None = None,
) -> dict[str, Any]:
    """Validate and materialize a process-event projection into Parquet files."""
    event_inputs = sorted(events_path.glob("*.jsonl")) if events_path.is_dir() else [events_path]
    if not event_inputs:
        raise ValueError(f"no JSONL event shards found in {events_path}")
    raw_events = merge_process_event_logs(event_inputs)
    takedown_ids = _read_takedown_ids(takedown_path)
    filtered_events = [
        row
        for row in raw_events
        if row.get("case_id") not in takedown_ids and row.get("event_id") not in takedown_ids
    ]
    events = _sort_events(_materialize_active_events(filtered_events))
    _validate_events(events)
    attachments = (
        _read_jsonl(attachments_path) if attachments_path and attachments_path.exists() else []
    )
    attachments = [
        row
        for row in attachments
        if row.get("case_id") not in takedown_ids and row.get("event_id") not in takedown_ids
    ]
    for row in attachments:
        if row.get("contract_version", CONTRACT_VERSION) != CONTRACT_VERSION:
            raise ValueError("unsupported attachment contract version")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path else {}
    source_reconciliation = {}
    if source_reconciliation_path and source_reconciliation_path.exists():
        source_reconciliation = json.loads(source_reconciliation_path.read_text(encoding="utf-8"))

    output_dir.mkdir(parents=True, exist_ok=True)
    event_columns = sorted({key for row in events for key in row})
    event_frame = pl.DataFrame(events).select(event_columns) if events else pl.DataFrame()
    event_path = output_dir / "events.parquet"
    case_path = output_dir / "cases.parquet"
    attachment_path = output_dir / "attachments.parquet"
    revision_path = output_dir / "revisions.parquet"
    event_frame.write_parquet(event_path)
    pl.DataFrame(_case_rows(events)).write_parquet(case_path)
    pl.DataFrame(attachments).write_parquet(attachment_path)
    revisions = [
        {
            "revision": snapshot_revision or "local",
            "captured_at": manifest.get("meta", {}).get("captured_at")
            or snapshot_revision
            or "local",
            "event_count": len(events),
            "case_count": len({row["case_id"] for row in events}),
        }
    ]
    pl.DataFrame(revisions).write_parquet(revision_path)

    expected_requests = manifest.get("meta", {}).get("record_count")
    manifest_requests = (
        manifest.get("requests") if isinstance(manifest.get("requests"), list) else []
    )
    expected_attachments = sum(
        len(request.get("attachments") or [])
        for request in manifest_requests
        if isinstance(request, dict)
    )
    attachment_input_supplied = attachments_path is not None
    coverage = {
        "contract_version": CONTRACT_VERSION,
        "source_events": [str(path) for path in event_inputs],
        "snapshot_revision": snapshot_revision,
        "event_count": len(events),
        "excluded_event_count": len(raw_events) - len(events),
        "retracted_event_count": sum(row.get("operation") == "retract" for row in filtered_events),
        "case_count": len({row["case_id"] for row in events}),
        "attachment_count": len(attachments),
        "manifest_attachment_count": expected_attachments if manifest_requests else None,
        "attachment_count_reconciles": (
            not attachment_input_supplied
            or not manifest_requests
            or expected_attachments == len(attachments)
        ),
        "takedown_ids": sorted(takedown_ids),
        "manifest_request_count": expected_requests,
        "request_count_reconciles": expected_requests is None
        or expected_requests == len({row["case_id"] for row in events}),
    }
    if isinstance(source_reconciliation, dict):
        coverage["source_reconciliation"] = {
            "schema": source_reconciliation.get("schema"),
            "candidate_count": source_reconciliation.get("candidate_count", 0),
            "counts": source_reconciliation.get("counts", {}),
        }
    coverage_path = output_dir / "coverage.json"
    coverage_path.write_text(
        json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    metadata = {
        "name": "fyi-archive-process-events",
        "version": CONTRACT_VERSION,
        "license": "Apache-2.0",
        "resources": [
            {"name": name, "path": f"{name}.parquet", "format": "parquet"}
            for name in ("events", "cases", "attachments", "revisions")
        ],
        "coverage": "coverage.json",
    }
    metadata_path = output_dir / "dataset_info.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_checksums(
        output_dir,
        [event_path, case_path, attachment_path, revision_path, coverage_path, metadata_path],
    )
    return coverage
