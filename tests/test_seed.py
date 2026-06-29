"""Tests for historical seed orchestration."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from fyi_archive.cli import app
from fyi_archive.seed import SeedCaps, SeedRequest, load_ledger, run_seed


def test_run_seed_dry_run_writes_ledger_and_derived_records(tmp_path: Path) -> None:
    ledger = tmp_path / "data/_state/ledger.jsonl"
    derived = tmp_path / "data/derived/requests"
    requests = [SeedRequest(request_id=1, url_title="one")]

    summary = run_seed(
        requests=requests,
        ledger_path=ledger,
        data_dir=tmp_path / "data",
        derived_dir=derived,
        caps=SeedCaps(max_requests=10),
        dry_run=True,
        date_from="2026-01-01",
        date_to="2026-01-31",
    )

    assert summary["processed"] == 1
    assert summary["date_from"] == "2026-01-01"
    assert load_ledger(ledger) == {1}
    assert json.loads((derived / "1.json").read_text(encoding="utf-8"))["url_title"] == "one"


def test_run_seed_resumes_completed_requests(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text('{"request_id": 1, "status": "completed"}\n', encoding="utf-8")

    summary = run_seed(
        requests=[SeedRequest(1, "one"), SeedRequest(2, "two")],
        ledger_path=ledger,
        data_dir=tmp_path / "data",
        derived_dir=tmp_path / "derived",
        caps=SeedCaps(max_requests=10),
        dry_run=True,
    )

    assert summary["processed"] == 1
    assert summary["skipped"] == 1
    assert load_ledger(ledger) == {1, 2}


def test_run_seed_stops_at_max_requests(tmp_path: Path) -> None:
    summary = run_seed(
        requests=[SeedRequest(1, "one"), SeedRequest(2, "two")],
        ledger_path=tmp_path / "ledger.jsonl",
        data_dir=tmp_path / "data",
        derived_dir=tmp_path / "derived",
        caps=SeedCaps(max_requests=1),
        dry_run=True,
    )

    assert summary["processed"] == 1
    assert summary["stop_reason"] == "max_requests"


def test_seed_cli_dry_run(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "seed",
            "run",
            "--dry-run",
            "--max-requests",
            "2",
            "--ledger-path",
            str(tmp_path / "ledger.jsonl"),
            "--data-dir",
            str(tmp_path / "data"),
            "--derived-dir",
            str(tmp_path / "derived"),
        ],
    )

    assert result.exit_code == 0
    assert '"processed": 2' in result.stdout
