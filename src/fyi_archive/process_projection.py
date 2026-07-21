"""Consume the versioned fyi-cli process-event projection.

The process projection is deliberately separate from the faithful archive
manifest.  It contains public-safe event, case, attachment metadata, and
revision rows suitable for process mining and Dataset Viewer ingestion.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

CONTRACT_VERSION = "1.0.0"
REQUIRED_EVENT_FIELDS = {"event_id", "case_id", "activity"}


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
        rows.append(value)
    return rows


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
            int(row.get("source_index", row.get("source_order", 0)) or 0),
            str(row.get("event_id", "")),
        ),
    )


def _case_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        grouped.setdefault(event["case_id"], []).append(event)
    result = []
    for case_id, case_events in grouped.items():
        result.append(
            {
                "case_id": case_id,
                "event_count": len(case_events),
                "first_source_index": min(
                    int(event.get("source_index", event.get("source_order", 0)) or 0)
                    for event in case_events
                ),
                "last_source_index": max(
                    int(event.get("source_index", event.get("source_order", 0)) or 0)
                    for event in case_events
                ),
            }
        )
    return sorted(result, key=lambda row: row["case_id"])


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


def build_process_projection(
    *,
    events_path: Path,
    output_dir: Path,
    manifest_path: Path | None = None,
    attachments_path: Path | None = None,
    snapshot_revision: str | None = None,
) -> dict[str, Any]:
    """Validate and materialize a process-event projection into Parquet files."""
    events = _sort_events(_read_jsonl(events_path))
    _validate_events(events)
    attachments = _read_jsonl(attachments_path) if attachments_path and attachments_path.exists() else []
    for row in attachments:
        if row.get("contract_version", CONTRACT_VERSION) != CONTRACT_VERSION:
            raise ValueError("unsupported attachment contract version")

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
            "captured_at": datetime.now(UTC).isoformat(),
            "event_count": len(events),
            "case_count": len({row["case_id"] for row in events}),
        }
    ]
    pl.DataFrame(revisions).write_parquet(revision_path)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path else {}
    expected_requests = manifest.get("meta", {}).get("record_count")
    coverage = {
        "contract_version": CONTRACT_VERSION,
        "source_events": str(events_path),
        "snapshot_revision": snapshot_revision,
        "event_count": len(events),
        "case_count": len({row["case_id"] for row in events}),
        "attachment_count": len(attachments),
        "manifest_request_count": expected_requests,
        "request_count_reconciles": expected_requests is None
        or expected_requests == len({row["case_id"] for row in events}),
    }
    coverage_path = output_dir / "coverage.json"
    coverage_path.write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_checksums(output_dir, [event_path, case_path, attachment_path, revision_path, coverage_path, metadata_path])
    return coverage
