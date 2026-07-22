from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest
from typer.testing import CliRunner

from fyi_archive.cli import app
from fyi_archive.process_projection import (
    build_process_projection,
    merge_process_event_logs,
    verify_process_projection,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_projection_preserves_source_order_and_writes_viewer_resources(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    _write_jsonl(
        events,
        [
            {"event_id": "e2", "case_id": "c1", "activity": "closed", "source_index": 2},
            {
                "event_id": "e1",
                "case_id": "c1",
                "activity": "opened",
                "source_order": {"event_sequence": 1},
            },
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


def test_projection_repeated_generation_has_stable_revision_metadata(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    _write_jsonl(
        events,
        [{"event_id": "e1", "case_id": "c1", "activity": "opened", "source_index": 1}],
    )
    first = tmp_path / "first"
    second = tmp_path / "second"
    build_process_projection(events_path=events, output_dir=first, snapshot_revision="snapshot-1")
    build_process_projection(events_path=events, output_dir=second, snapshot_revision="snapshot-1")
    assert (first / "revisions.parquet").read_bytes() == (second / "revisions.parquet").read_bytes()
    assert (first / "CHECKSUMS.sha256").read_text() == (second / "CHECKSUMS.sha256").read_text()


def test_projection_propagates_takedown_to_events_and_attachments(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    attachments = tmp_path / "attachments.jsonl"
    takedown = tmp_path / "takedown.jsonl"
    _write_jsonl(
        events,
        [
            {"event_id": "e1", "case_id": "c1", "activity": "opened"},
            {"event_id": "e2", "case_id": "c2", "activity": "opened"},
        ],
    )
    _write_jsonl(attachments, [{"case_id": "c1", "sha256": "a"}, {"case_id": "c2", "sha256": "b"}])
    _write_jsonl(takedown, [{"case_id": "c1", "reason": "removal"}])
    output = tmp_path / "out"
    coverage = build_process_projection(
        events_path=events,
        attachments_path=attachments,
        takedown_path=takedown,
        output_dir=output,
    )
    assert coverage["excluded_event_count"] == 1
    assert coverage["takedown_ids"] == ["c1"]
    assert pl.read_parquet(output / "events.parquet")["case_id"].to_list() == ["c2"]
    assert pl.read_parquet(output / "attachments.parquet")["case_id"].to_list() == ["c2"]


def test_merge_is_idempotent_and_rejects_conflicting_revisions(tmp_path: Path) -> None:
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    row = {
        "event_id": "e1",
        "logical_event_id": "le1",
        "revision": 1,
        "case_id": "c1",
        "activity": "opened",
    }
    _write_jsonl(first, [row])
    _write_jsonl(second, [row])
    assert merge_process_event_logs([first, second]) == [row]
    conflicting = dict(row)
    conflicting["activity"] = "closed"
    _write_jsonl(second, [conflicting])
    with pytest.raises(ValueError, match="conflicting payloads"):
        merge_process_event_logs([first, second])


def test_projection_applies_latest_retraction_tombstone(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    _write_jsonl(
        events,
        [
            {
                "event_id": "e1",
                "logical_event_id": "le1",
                "revision": 1,
                "case_id": "c1",
                "activity": "opened",
                "operation": "upsert",
            },
            {
                "event_id": "e2",
                "logical_event_id": "le1",
                "revision": 2,
                "case_id": "c1",
                "activity": "opened",
                "operation": "retract",
            },
        ],
    )
    output = tmp_path / "out"
    coverage = build_process_projection(events_path=events, output_dir=output)
    assert coverage["event_count"] == 0
    assert coverage["retracted_event_count"] == 1
    assert pl.read_parquet(output / "events.parquet").height == 0


def test_projection_consumes_resumed_event_shards_deterministically(tmp_path: Path) -> None:
    shards = tmp_path / "shards"
    shards.mkdir()
    _write_jsonl(
        shards / "002.jsonl",
        [{"event_id": "e2", "logical_event_id": "le2", "revision": 1, "case_id": "c1", "activity": "closed"}],
    )
    _write_jsonl(
        shards / "001.jsonl",
        [{"event_id": "e1", "logical_event_id": "le1", "revision": 1, "case_id": "c1", "activity": "opened"}],
    )
    output = tmp_path / "out"
    coverage = build_process_projection(events_path=shards, output_dir=output)
    assert coverage["event_count"] == 2
    assert pl.read_parquet(output / "events.parquet")["event_id"].to_list() == ["e1", "e2"]


def test_projection_reconciles_manifest_attachment_coverage(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    manifest = tmp_path / "manifest.json"
    attachments = tmp_path / "attachments.jsonl"
    _write_jsonl(events, [{"event_id": "e1", "case_id": "c1", "activity": "opened"}])
    manifest.write_text(
        json.dumps({"meta": {"record_count": 1}, "requests": [{"attachments": [{"sha256": "a"}]}]}),
        encoding="utf-8",
    )
    _write_jsonl(attachments, [{"case_id": "c1", "sha256": "a"}])
    coverage = build_process_projection(
        events_path=events,
        manifest_path=manifest,
        attachments_path=attachments,
        output_dir=tmp_path / "out",
    )
    assert coverage["manifest_attachment_count"] == 1
    assert coverage["attachment_count_reconciles"] is True


def test_projection_includes_historical_source_reconciliation(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    reconciliation = tmp_path / "reconciliation.json"
    _write_jsonl(events, [{"event_id": "e1", "case_id": "c1", "activity": "opened"}])
    reconciliation.write_text(
        json.dumps({
            "schema": "historical-source-reconciliation-v1",
            "candidate_count": 4,
            "counts": {"archive_only_candidate": 3, "live_captured": 1},
        }),
        encoding="utf-8",
    )
    coverage = build_process_projection(
        events_path=events,
        source_reconciliation_path=reconciliation,
        output_dir=tmp_path / "out",
    )
    assert coverage["source_reconciliation"]["candidate_count"] == 4
    assert coverage["source_reconciliation"]["counts"]["archive_only_candidate"] == 3


def test_process_verify_rejects_manifest_event_count_mismatch(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "out"
    _write_jsonl(events, [{"event_id": "e1", "case_id": "c1", "activity": "opened"}])
    manifest.write_text(
        json.dumps({"meta": {"record_count": 2}, "requests": [{}, {}]}),
        encoding="utf-8",
    )

    build_process_projection(events_path=events, manifest_path=manifest, output_dir=output)

    with pytest.raises(ValueError, match="request_count_reconciles"):
        verify_process_projection(output)


def test_projection_rejects_wrong_contract(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    _write_jsonl(
        events,
        [{"event_id": "e1", "case_id": "c1", "activity": "opened", "contract_version": "9.0.0"}],
    )
    with pytest.raises(ValueError, match="unsupported"):
        build_process_projection(events_path=events, output_dir=tmp_path / "out")


def test_projection_accepts_fyi_cli_logical_request_id(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    _write_jsonl(
        events,
        [
            {
                "event_id": "e1",
                "logical_request_id": "urn:fyi:nz-fyi:request:7",
                "activity": "opened",
                "source_order": {"event_sequence": 0},
            }
        ],
    )
    coverage = build_process_projection(events_path=events, output_dir=tmp_path / "out")
    assert coverage["case_count"] == 1


def test_process_cli_projects_and_verifies(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    _write_jsonl(events, [{"event_id": "e1", "case_id": "c1", "activity": "opened"}])
    output = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(
        app, ["process", "project", "--events", str(events), "--output-dir", str(output)]
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["process", "verify", "--output-dir", str(output)])
    assert result.exit_code == 0, result.output


def test_projection_rejects_malformed_json(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    events.write_text("not-json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        build_process_projection(events_path=events, output_dir=tmp_path / "out")

    events.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must be an object"):
        build_process_projection(events_path=events, output_dir=tmp_path / "out")


@pytest.mark.parametrize("field", ["event_id", "case_id"])
def test_projection_rejects_empty_identity(tmp_path: Path, field: str) -> None:
    events = tmp_path / "events.jsonl"
    row: dict[str, object] = {"event_id": "e1", "case_id": "c1", "activity": "opened"}
    row[field] = ""
    _write_jsonl(events, [row])
    with pytest.raises(ValueError, match="invalid"):
        build_process_projection(events_path=events, output_dir=tmp_path / "out")


def test_process_cli_reports_projection_and_checksum_errors(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    _write_jsonl(events, [{"event_id": "e1", "case_id": "c1"}])
    runner = CliRunner()
    result = runner.invoke(app, ["process", "project", "--events", str(events)])
    assert result.exit_code != 0
    result = runner.invoke(app, ["process", "verify", "--output-dir", str(tmp_path / "missing")])
    assert result.exit_code != 0
