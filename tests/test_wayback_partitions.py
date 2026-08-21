from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from fyi_archive.wayback_partitions import (
    TimePartition,
    build_year_partitions,
    merge_complete_partition_exports,
)


def _partition_files(
    root: Path, partition: TimePartition, rows: list[list[str]], *, complete: bool = True
) -> tuple[TimePartition, Path, Path]:
    export = root / f"{partition.id}.json"
    retrieval = root / f"{partition.id}.evidence.json"
    payload = [["urlkey", "original", "timestamp"], *rows]
    raw = json.dumps(payload, indent=2) + "\n"
    export.write_bytes(raw.encode())
    retrieval.write_text(
        json.dumps(
            {
                "retrieval_status": "complete" if complete else "failed",
                "pagination_complete": complete,
                "from_timestamp": partition.from_timestamp,
                "to_timestamp": partition.to_timestamp,
                "record_count": len(rows),
                "response_sha256": hashlib.sha256(raw.encode()).hexdigest() if complete else None,
            }
        ),
        encoding="utf-8",
    )
    return partition, export, retrieval


def test_builds_stable_closed_buckets_and_one_open_partition() -> None:
    partitions = build_year_partitions(start_year=1996, open_from_year=2025, span_years=5)
    assert partitions[0] == TimePartition("1996-2000", "1996", "2000")
    assert partitions[-2] == TimePartition("2021-2024", "2021", "2024")
    assert partitions[-1] == TimePartition("2025-open", "2025", None)


def test_merge_requires_every_partition_and_deduplicates_by_urlkey(tmp_path: Path) -> None:
    early = TimePartition("1996-2024", "1996", "2024")
    recent = TimePartition("2025-open", "2025", None)
    partitions = [
        _partition_files(
            tmp_path,
            early,
            [["org,example)/request/a", "https://example.org/request/a", "1999"]],
        ),
        _partition_files(
            tmp_path,
            recent,
            [
                ["org,example)/request/a", "https://example.org/request/a", "2025"],
                ["org,example)/request/b", "https://example.org/request/b", "2026"],
            ],
        ),
    ]
    output = tmp_path / "merged.json"
    evidence_path = tmp_path / "merged.evidence.json"

    evidence = merge_complete_partition_exports(
        partitions, output=output, evidence_output=evidence_path
    )

    payload = json.loads(output.read_text())
    assert evidence["record_count"] == 2
    assert payload[1][2] == "1999"
    assert hashlib.sha256(output.read_bytes()).hexdigest() == evidence["response_sha256"]


def test_merge_fails_closed_before_writing_partial_output(tmp_path: Path) -> None:
    partition = TimePartition("2025-open", "2025", None)
    item = _partition_files(tmp_path, partition, [], complete=False)
    output = tmp_path / "merged.json"

    with pytest.raises(RuntimeError, match="incomplete"):
        merge_complete_partition_exports(
            [item], output=output, evidence_output=tmp_path / "evidence.json"
        )

    assert not output.exists()


def test_merge_rejects_gapped_or_closed_final_partition(tmp_path: Path) -> None:
    early = TimePartition("1996-2000", "1996", "2000")
    recent = TimePartition("2025-open", "2025", None)
    items = [
        _partition_files(tmp_path, early, []),
        _partition_files(tmp_path, recent, []),
    ]
    with pytest.raises(ValueError, match="contiguous"):
        merge_complete_partition_exports(
            [(TimePartition("1996-1999", "1996", "1999"), *items[0][1:]), items[1]],
            output=tmp_path / "gapped.json",
            evidence_output=tmp_path / "gapped-evidence.json",
        )
    with pytest.raises(ValueError, match="final partition"):
        merge_complete_partition_exports(
            [items[0]],
            output=tmp_path / "closed.json",
            evidence_output=tmp_path / "closed-evidence.json",
        )


@pytest.mark.parametrize(
    ("partition_id", "start", "end", "message"),
    [
        ("Bad Id", "2020", None, "kebab"),
        ("bad", "20", None, "from_timestamp"),
        ("bad", "2020", "20", "to_timestamp"),
        ("bad", "2021", "2020", "must not exceed"),
    ],
)
def test_time_partition_rejects_invalid_values(
    partition_id: str, start: str, end: str | None, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        TimePartition(partition_id, start, end)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"start_year": 999, "open_from_year": 2020}, "four digits"),
        ({"start_year": 2020, "open_from_year": 2020}, "must precede"),
        ({"start_year": 2000, "open_from_year": 2020, "span_years": 0}, "positive"),
    ],
)
def test_build_partitions_rejects_invalid_ranges(kwargs: dict[str, int], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        build_year_partitions(**kwargs)


def test_merge_rejects_empty_duplicate_and_nonfinal_open_plans(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least one"):
        merge_complete_partition_exports(
            [], output=tmp_path / "out.json", evidence_output=tmp_path / "evidence.json"
        )
    final = TimePartition("2025-open", "2025", None)
    item = _partition_files(tmp_path, final, [])
    with pytest.raises(ValueError, match="unique"):
        merge_complete_partition_exports(
            [item, item], output=tmp_path / "dup.json", evidence_output=tmp_path / "dup-e.json"
        )
    with pytest.raises(ValueError, match="only the final"):
        merge_complete_partition_exports(
            [item, _partition_files(tmp_path, TimePartition("2026-open", "2026", None), [])],
            output=tmp_path / "open.json",
            evidence_output=tmp_path / "open-e.json",
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update(from_timestamp="2000"), "time range"),
        (lambda value: value.update(response_sha256="bad"), "response hash"),
        (lambda value: value.update(record_count=99), "record count"),
    ],
)
def test_merge_rejects_invalid_retrieval_evidence(
    tmp_path: Path, mutation: Callable[[dict[str, Any]], None], message: str
) -> None:
    partition = TimePartition("2025-open", "2025", None)
    item = _partition_files(tmp_path, partition, [])
    retrieval = json.loads(item[2].read_text())
    mutation(retrieval)
    item[2].write_text(json.dumps(retrieval), encoding="utf-8")
    with pytest.raises(RuntimeError, match=message):
        merge_complete_partition_exports(
            [item], output=tmp_path / "out.json", evidence_output=tmp_path / "evidence.json"
        )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"not": "a list"}, "malformed"),
        ([["original", "timestamp"]], "requires urlkey"),
        (
            [["urlkey", "timestamp"], ["key-only"]],
            "row width",
        ),
    ],
)
def test_merge_rejects_malformed_exports(tmp_path: Path, payload: object, message: str) -> None:
    partition = TimePartition("2025-open", "2025", None)
    item = _partition_files(tmp_path, partition, [])
    raw = json.dumps(payload)
    item[1].write_text(raw, encoding="utf-8")
    retrieval = json.loads(item[2].read_text())
    retrieval["response_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
    retrieval["record_count"] = len(payload) - 1 if isinstance(payload, list) else 0
    item[2].write_text(json.dumps(retrieval), encoding="utf-8")
    with pytest.raises(RuntimeError, match=message):
        merge_complete_partition_exports(
            [item], output=tmp_path / "out.json", evidence_output=tmp_path / "evidence.json"
        )
