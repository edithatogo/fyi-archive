from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from fyi_archive.process_projection import build_process_projection, verify_process_projection


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_projection_preserves_source_order_and_writes_viewer_resources(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    _write_jsonl(
        events,
        [
            {"event_id": "e2", "case_id": "c1", "activity": "closed", "source_index": 2},
            {"event_id": "e1", "case_id": "c1", "activity": "opened", "source_index": 1},
        ],
    )
    output = tmp_path / "projection"
    coverage = build_process_projection(events_path=events, output_dir=output)
    assert coverage["event_count"] == 2
    assert pl.read_parquet(output / "events.parquet")["event_id"].to_list() == ["e1", "e2"]
    assert {path.name for path in output.glob("*.parquet")} == {
        "events.parquet",
        "cases.parquet",
        "attachments.parquet",
        "revisions.parquet",
    }
    assert (output / "CHECKSUMS.sha256").exists()
    verify_process_projection(output)
    (output / "events.parquet").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_process_projection(output)


def test_projection_rejects_wrong_contract(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    _write_jsonl(
        events,
        [{"event_id": "e1", "case_id": "c1", "activity": "opened", "contract_version": "9.0.0"}],
    )
    with pytest.raises(ValueError, match="unsupported"):
        build_process_projection(events_path=events, output_dir=tmp_path / "out")
