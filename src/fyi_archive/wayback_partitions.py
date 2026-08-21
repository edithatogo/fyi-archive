"""Deterministic time partitions and complete-only Wayback export merging."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

PARTITION_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class TimePartition:
    """One inclusive, non-overlapping CDX timestamp range."""

    id: str
    from_timestamp: str
    to_timestamp: str | None

    def __post_init__(self) -> None:
        """Reject ambiguous partition identifiers and ranges."""
        if not PARTITION_ID.fullmatch(self.id):
            raise ValueError("partition id must be lowercase kebab-case")
        if len(self.from_timestamp) != 4 or not self.from_timestamp.isdigit():
            raise ValueError("partition from_timestamp must be a four-digit year")
        if self.to_timestamp is not None and (
            len(self.to_timestamp) != 4 or not self.to_timestamp.isdigit()
        ):
            raise ValueError("partition to_timestamp must be a four-digit year")
        if self.to_timestamp is not None and int(self.from_timestamp) > int(self.to_timestamp):
            raise ValueError("partition start must not exceed its end")


def build_year_partitions(
    *, start_year: int, open_from_year: int, span_years: int = 5
) -> tuple[TimePartition, ...]:
    """Build stable closed year buckets plus one open-ended current bucket."""
    if start_year < 1000 or open_from_year < 1000:
        raise ValueError("partition years must use four digits")
    if start_year >= open_from_year:
        raise ValueError("start_year must precede open_from_year")
    if span_years < 1:
        raise ValueError("span_years must be positive")
    partitions: list[TimePartition] = []
    lower = start_year
    while lower < open_from_year:
        upper = min(lower + span_years - 1, open_from_year - 1)
        partitions.append(TimePartition(f"{lower}-{upper}", str(lower), str(upper)))
        lower = upper + 1
    partitions.append(TimePartition(f"{open_from_year}-open", str(open_from_year), None))
    return tuple(partitions)


def merge_complete_partition_exports(
    partitions: list[tuple[TimePartition, Path, Path]],
    *,
    output: Path,
    evidence_output: Path,
) -> dict[str, object]:
    """Merge only complete, hash-valid partitions and deduplicate by CDX urlkey."""
    if not partitions:
        raise ValueError("at least one partition is required")
    ids = [partition.id for partition, _, _ in partitions]
    if len(ids) != len(set(ids)):
        raise ValueError("partition ids must be unique")
    for index, (partition, _, _) in enumerate(partitions):
        if index == len(partitions) - 1:
            if partition.to_timestamp is not None:
                raise ValueError("the final partition must be open-ended")
            continue
        if partition.to_timestamp is None:
            raise ValueError("only the final partition may be open-ended")
        next_partition = partitions[index + 1][0]
        if int(next_partition.from_timestamp) != int(partition.to_timestamp) + 1:
            raise ValueError("partition years must be ordered, contiguous, and non-overlapping")

    header: list[str] | None = None
    rows_by_urlkey: dict[str, list[str]] = {}
    partition_evidence: list[dict[str, object]] = []
    for partition, export_path, retrieval_path in partitions:
        retrieval = json.loads(retrieval_path.read_text(encoding="utf-8"))
        if retrieval.get("retrieval_status") != "complete" or not retrieval.get(
            "pagination_complete"
        ):
            raise RuntimeError(f"partition {partition.id} is incomplete")
        if (
            retrieval.get("from_timestamp") != partition.from_timestamp
            or retrieval.get("to_timestamp") != partition.to_timestamp
        ):
            raise RuntimeError(f"partition {partition.id} time range does not match its plan")
        export_sha256 = hashlib.sha256(export_path.read_bytes()).hexdigest()
        if retrieval.get("response_sha256") != export_sha256:
            raise RuntimeError(f"partition {partition.id} response hash does not match")
        payload = json.loads(export_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list) or not payload or not isinstance(payload[0], list):
            raise RuntimeError(f"partition {partition.id} export is malformed")
        current_header = [str(value) for value in payload[0]]
        if len(payload) - 1 != int(retrieval["record_count"]):
            raise RuntimeError(f"partition {partition.id} record count does not match")
        if "urlkey" not in current_header or "timestamp" not in current_header:
            raise RuntimeError(f"partition {partition.id} export requires urlkey and timestamp")
        if header is None:
            header = current_header
        elif current_header != header:
            raise RuntimeError("partition headers are inconsistent")
        urlkey_index = current_header.index("urlkey")
        timestamp_index = current_header.index("timestamp")
        for raw_row in payload[1:]:
            row = [str(value) for value in raw_row]
            if len(row) != len(current_header):
                raise RuntimeError(f"partition {partition.id} row width is inconsistent")
            urlkey = row[urlkey_index]
            existing = rows_by_urlkey.get(urlkey)
            if existing is None or (row[timestamp_index], row) < (
                existing[timestamp_index],
                existing,
            ):
                rows_by_urlkey[urlkey] = row
        partition_evidence.append({
            **asdict(partition),
            "record_count": int(retrieval["record_count"]),
            "response_sha256": export_sha256,
        })

    if header is None:
        raise RuntimeError("partition merge produced no header")
    merged_rows = [rows_by_urlkey[key] for key in sorted(rows_by_urlkey)]
    raw = json.dumps([header, *merged_rows], indent=2) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw.encode())
    evidence: dict[str, object] = {
        "schema": "fyi-archive.wayback-partition-merge.v1",
        "complete": True,
        "deduplication_key": "urlkey",
        "selection": "earliest-timestamp",
        "record_count": len(merged_rows),
        "response_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "partitions": partition_evidence,
    }
    evidence_output.parent.mkdir(parents=True, exist_ok=True)
    evidence_output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return evidence
