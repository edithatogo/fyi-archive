"""Tests for historical seed orchestration."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from fyi_archive.cli import app
from fyi_archive.seed import (
    CaptureError,
    SeedCaps,
    SeedRequest,
    capture_with_fyi_cli,
    capture_with_retry,
    load_ledger,
    requests_from_id_range,
    requests_from_jsonl,
    run_seed,
)


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


def test_requests_from_jsonl_loads_discovered_rows(tmp_path: Path) -> None:
    requests_path = tmp_path / "requests.jsonl"
    requests_path.write_text(
        "\n".join(
            [
                "",
                '{"request_id": 20000, "url_title": "request-20000", "title": "Title", "authority": "agency"}',
            ],
        )
        + "\n",
        encoding="utf-8",
    )

    rows = requests_from_jsonl(requests_path)

    assert rows == [SeedRequest(20000, "request-20000", "Title", "agency")]


def test_requests_from_jsonl_preserves_slug_request_reference(tmp_path: Path) -> None:
    requests_path = tmp_path / "slug.jsonl"
    slug = "solicitud_de_" + "inform" + "acion_sobre_r"
    requests_path.write_text(
        json.dumps({"request_id": slug, "url_title": slug}) + "\n",
        encoding="utf-8",
    )
    assert requests_from_jsonl(requests_path) == [SeedRequest(slug, slug)]


def test_requests_from_id_range_builds_fallback_queue() -> None:
    rows = requests_from_id_range(20000, 20002)

    assert rows == [
        SeedRequest(20000, "request-20000"),
        SeedRequest(20001, "request-20001"),
        SeedRequest(20002, "request-20002"),
    ]


def test_capture_with_fyi_cli_builds_current_capture_command(tmp_path: Path, monkeypatch) -> None:
    calls = []

    def fake_run(command, **kwargs):  # noqa: ANN001, ANN202
        calls.append((command, kwargs))
        return SimpleNamespace(stdout='{"derived_path": "derived/20000"}')

    monkeypatch.setattr(subprocess, "run", fake_run)

    summary = capture_with_fyi_cli(
        SeedRequest(20000, "request-20000"),
        tmp_path / "data",
        tmp_path / "dist",
        SeedCaps(max_bytes=100, max_runtime_minutes=2, max_disk_gb=1),
        ("--base-url", "https://fyi.example"),
    )

    command, kwargs = calls[0]
    assert command[1:5] == ["-m", "fyi_system.cli", "capture", "20000"]
    assert "--data-dir" in command
    assert "--dist-dir" in command
    assert "--max-bytes" in command
    assert "--max-runtime-minutes" in command
    assert "--max-disk-gb" in command
    assert "--base-url" in command
    assert kwargs == {"check": True, "capture_output": True, "text": True, "timeout": 150}
    assert summary == {"derived_path": "derived/20000"}


def test_capture_with_fyi_cli_converts_subprocess_timeout_to_capture_error(
    tmp_path: Path, monkeypatch
) -> None:
    def timed_out(command, **kwargs):  # noqa: ANN001, ANN202
        raise subprocess.TimeoutExpired(command, kwargs["timeout"], stderr="hung")

    monkeypatch.setattr(subprocess, "run", timed_out)
    with pytest.raises(CaptureError) as raised:
        capture_with_fyi_cli(
            SeedRequest(20000, "request-20000"),
            tmp_path / "data",
            tmp_path / "dist",
            SeedCaps(max_runtime_minutes=1),
            (),
        )
    assert raised.value.returncode == 124
    assert "hung" in raised.value.stderr


def test_run_seed_non_dry_run_records_capture_summary(tmp_path: Path, monkeypatch) -> None:
    derived_path = tmp_path / "data" / "raw" / "requests" / "agency" / "20000"
    derived_path.mkdir(parents=True)
    (derived_path / "request.json").write_text("{}", encoding="utf-8")

    def fake_capture(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        return {"derived_path": derived_path.as_posix()}

    monkeypatch.setattr("fyi_archive.seed.capture_with_fyi_cli", fake_capture)

    summary = run_seed(
        requests=[SeedRequest(20000, "request-20000")],
        ledger_path=tmp_path / "ledger.jsonl",
        data_dir=tmp_path / "data",
        derived_dir=tmp_path / "unused",
        dist_dir=tmp_path / "dist",
        caps=SeedCaps(max_requests=1),
        dry_run=False,
    )

    assert summary["processed"] == 1
    assert load_ledger(tmp_path / "ledger.jsonl") == {20000}


def test_run_seed_enforces_interval_between_live_captures(tmp_path: Path, monkeypatch) -> None:
    captured = []
    sleeps = []

    def fake_capture(request, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        captured.append(request.request_id)
        return {"derived_path": str(tmp_path / f"derived-{request.request_id}")}

    clock = iter([0.0, 0.0, 1.0, 1.0, 2.0])
    monkeypatch.setattr("fyi_archive.seed.capture_with_fyi_cli", fake_capture)
    monkeypatch.setattr("fyi_archive.seed.time.monotonic", lambda: next(clock))
    monkeypatch.setattr("fyi_archive.seed.time.sleep", sleeps.append)

    summary = run_seed(
        requests=[SeedRequest(1, "one"), SeedRequest(2, "two")],
        ledger_path=tmp_path / "ledger.jsonl",
        data_dir=tmp_path / "data",
        derived_dir=tmp_path / "derived",
        caps=SeedCaps(max_requests=2),
        dry_run=False,
        min_interval_seconds=30,
    )

    assert summary["processed"] == 2
    assert captured == [1, 2]
    assert sleeps == [29.0]


def test_run_seed_can_continue_after_capture_failure(tmp_path: Path, monkeypatch) -> None:
    def fake_capture(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise CaptureError(
            request_id=20000,
            command=["fyi", "capture", "20000"],
            returncode=1,
            stdout="out",
            stderr="err",
        )

    monkeypatch.setattr("fyi_archive.seed.capture_with_fyi_cli", fake_capture)

    summary = run_seed(
        requests=[SeedRequest(20000, "request-20000")],
        ledger_path=tmp_path / "ledger.jsonl",
        data_dir=tmp_path / "data",
        derived_dir=tmp_path / "unused",
        dist_dir=tmp_path / "dist",
        caps=SeedCaps(max_requests=1),
        dry_run=False,
        continue_on_error=True,
    )

    ledger = [
        json.loads(line)
        for line in (tmp_path / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert summary["processed"] == 0
    assert summary["failed"] == 1
    assert ledger[0]["status"] == "failed"
    assert ledger[0]["stderr_tail"] == "err"


def test_capture_with_retry_recovers_from_transient_timeout(tmp_path: Path, monkeypatch) -> None:
    attempts = {"count": 0}

    def fake_capture(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise CaptureError(
                request_id=20000,
                command=["fyi", "capture", "20000"],
                returncode=1,
                stdout="",
                stderr="httpx.ReadTimeout: The read operation timed out",
            )
        return {"derived_path": (tmp_path / "derived" / "20000").as_posix()}

    monkeypatch.setattr("fyi_archive.seed.capture_with_fyi_cli", fake_capture)
    monkeypatch.setattr("fyi_archive.seed.time.sleep", lambda _seconds: None)

    summary = capture_with_retry(
        SeedRequest(20000, "request-20000"),
        tmp_path / "data",
        tmp_path / "dist",
        SeedCaps(max_requests=1),
        (),
        retry_attempts=2,
        retry_backoff_seconds=0,
    )

    assert attempts["count"] == 2
    assert summary == {"derived_path": (tmp_path / "derived" / "20000").as_posix()}


def test_capture_with_retry_does_not_retry_non_transient_failure(
    tmp_path: Path, monkeypatch
) -> None:
    attempts = {"count": 0}

    def fake_capture(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        attempts["count"] += 1
        raise CaptureError(
            request_id=20000,
            command=["fyi", "capture", "20000"],
            returncode=1,
            stdout="",
            stderr="permission denied",
        )

    monkeypatch.setattr("fyi_archive.seed.capture_with_fyi_cli", fake_capture)
    monkeypatch.setattr("fyi_archive.seed.time.sleep", lambda _seconds: None)

    with pytest.raises(CaptureError):
        capture_with_retry(
            SeedRequest(20000, "request-20000"),
            tmp_path / "data",
            tmp_path / "dist",
            SeedCaps(max_requests=1),
            (),
            retry_attempts=3,
            retry_backoff_seconds=0,
        )

    assert attempts["count"] == 1


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
