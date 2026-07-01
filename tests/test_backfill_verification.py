"""Tests for the backfill verification report."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import respx
from httpx import Response
from typer.testing import CliRunner

from fyi_archive.backfill_verification import (
    build_backfill_verification_report,
    load_controller_state,
    remote_huggingface_record_count,
    remote_zenodo_record_count,
)
from fyi_archive.cli import app

runner = CliRunner()


def _completed(stdout: object) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["gh"],
        returncode=0,
        stdout=json.dumps(stdout),
        stderr="",
    )


def test_load_controller_state_selects_exact_issue(monkeypatch) -> None:
    state = {"next_id": 7001, "batches": []}

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        args = cmd[1:]
        if args[:2] == ["issue", "list"] and "open" in args:
            return _completed(
                [
                    {
                        "number": 1,
                        "title": "Unrelated",
                        "url": "https://github.com/example/repo/issues/1",
                    },
                    {
                        "number": 9,
                        "title": "FYI historical backfill state (fyi-backfill-state)",
                        "url": "https://github.com/example/repo/issues/9",
                    },
                ],
            )
        if args[:2] == ["issue", "view"]:
            return _completed({"body": json.dumps(state)})
        raise AssertionError(args)

    monkeypatch.setattr("fyi_archive.backfill_verification.subprocess.run", fake_run)

    loaded = load_controller_state(repo="example/repo", state_label="fyi-backfill-state")

    assert loaded["issue_number"] == 9
    assert loaded["state"] == state


def test_load_controller_state_falls_back_to_closed_issue(monkeypatch) -> None:
    state = {"next_id": 1, "batches": []}

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        args = cmd[1:]
        if args[:2] == ["issue", "list"] and "open" in args:
            return _completed([])
        if args[:2] == ["issue", "list"] and "all" in args:
            return _completed(
                [
                    {
                        "number": 9,
                        "title": "FYI historical backfill state (fyi-backfill-state)",
                        "url": "https://github.com/example/repo/issues/9",
                    }
                ],
            )
        if args[:2] == ["issue", "view"]:
            return _completed({"body": json.dumps(state)})
        raise AssertionError(args)

    monkeypatch.setattr("fyi_archive.backfill_verification.subprocess.run", fake_run)

    loaded = load_controller_state(repo="example/repo", state_label="fyi-backfill-state")

    assert loaded["issue_number"] == 9
    assert loaded["state"]["next_id"] == 1


def test_load_controller_state_rejects_bad_issue_body(monkeypatch) -> None:
    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        args = cmd[1:]
        if args[:2] == ["issue", "view"] and "body,url,title,number" in args:
            return _completed({"number": 9, "title": "state", "url": "https://example.test/9"})
        if args[:2] == ["issue", "view"] and "body" in args:
            return _completed({"body": "not-json"})
        raise AssertionError(args)

    monkeypatch.setattr("fyi_archive.backfill_verification.subprocess.run", fake_run)

    try:
        load_controller_state(
            repo="example/repo",
            state_label="fyi-backfill-state",
            issue_number=9,
        )
    except ValueError as exc:
        assert "does not contain JSON state" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_backfill_report_cli_writes_versioned_reports(tmp_path: Path, monkeypatch) -> None:
    manifest = tmp_path / "manifests/latest_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"meta": {"record_count": 3}, "requests": []}\n', encoding="utf-8")

    state_info = {
        "issue_number": 9,
        "issue_url": "https://github.com/example/repo/issues/9",
        "issue_title": "FYI historical backfill state (fyi-backfill-state)",
        "state": {
            "complete": False,
            "id_from": 1,
            "id_to": 100,
            "next_id": 4,
            "batches": [
                {
                    "id_from": "1",
                    "id_to": "3",
                    "label": "1-3",
                    "status": "merged",
                    "record_count": 3,
                    "worker_run_id": "123",
                }
            ],
            "dispatched": [{"controller_run_id": "456"}],
        },
    }

    monkeypatch.setattr(
        "fyi_archive.commands.backfill.load_controller_state",
        lambda **kwargs: state_info,
    )
    monkeypatch.setattr(
        "fyi_archive.commands.backfill.remote_huggingface_record_count",
        lambda **kwargs: {"repo_id": kwargs["repo_id"], "revision": None, "record_count": 3},
    )
    monkeypatch.setattr(
        "fyi_archive.commands.backfill.remote_zenodo_record_count",
        lambda **kwargs: {
            "deposition_id": kwargs["deposition_id"],
            "doi": "10.5281/zenodo.42",
            "api_url": kwargs["api_url"],
            "record_count": 3,
        },
    )
    monkeypatch.setattr(
        "fyi_archive.backfill_verification.utc_now",
        lambda: datetime(2026, 6, 30, tzinfo=UTC),
    )

    result = runner.invoke(
        app,
        [
            "backfill",
            "report",
            "--repo",
            "example/repo",
            "--state-label",
            "fyi-backfill-state",
            "--manifest-path",
            str(manifest),
            "--output-path",
            str(tmp_path / "dist/backfill_verification.json"),
            "--output-dir",
            str(tmp_path / "versions"),
            "--hf-repo-id",
            "owner/dataset",
            "--hf-token",
            "hf-token",
            "--zenodo-deposition-id",
            "42",
            "--zenodo-token",
            "zenodo-token",
            "--zenodo-api-url",
            "https://zenodo.example/api",
        ],
    )

    assert result.exit_code == 0, result.output
    report_path = tmp_path / "dist/backfill_verification.json"
    latest_path = tmp_path / "versions/latest_backfill_verification.json"
    month_path = tmp_path / "versions/2026-06/backfill_verification.json"
    assert report_path.exists()
    assert latest_path.exists()
    assert month_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["github_actions"]["captured_records"] == 3
    assert report["published"]["huggingface"]["record_count"] == 3
    assert report["comparison"]["fully_verified"] is True
    assert report["dry_run"] is False


def test_backfill_report_cli_allows_dry_run_without_full_verification(
    tmp_path: Path, monkeypatch
) -> None:
    manifest = tmp_path / "manifests/latest_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"meta": {"record_count": 2}, "requests": []}\n', encoding="utf-8")

    state_info = {
        "issue_number": 9,
        "issue_url": "https://github.com/example/repo/issues/9",
        "issue_title": "FYI historical backfill state (fyi-backfill-state)",
        "state": {
            "complete": False,
            "id_from": 1,
            "id_to": 100,
            "next_id": 4,
            "batches": [],
            "dispatched": [],
        },
    }

    monkeypatch.setattr(
        "fyi_archive.commands.backfill.load_controller_state",
        lambda **kwargs: state_info,
    )
    monkeypatch.setattr(
        "fyi_archive.backfill_verification.utc_now",
        lambda: datetime(2026, 6, 30, tzinfo=UTC),
    )

    result = runner.invoke(
        app,
        [
            "backfill",
            "report",
            "--repo",
            "example/repo",
            "--state-label",
            "fyi-backfill-state",
            "--manifest-path",
            str(manifest),
            "--output-path",
            str(tmp_path / "dist/backfill_verification.json"),
            "--output-dir",
            str(tmp_path / "versions"),
        ],
        env={"DRY_RUN": "true"},
    )

    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path / "dist/backfill_verification.json").read_text(encoding="utf-8"))
    assert report["dry_run"] is True
    assert report["comparison"]["fully_verified"] is False


def test_backfill_report_flags_published_ids_outside_merged_controller_ranges(
    tmp_path: Path, monkeypatch
) -> None:
    manifest = tmp_path / "manifests/latest_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "meta": {"record_count": 3},
                "requests": [
                    {"request_id": 10},
                    {"request_id": 2010},
                    {"request_id": 2020},
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    state_info = {
        "issue_number": 9,
        "issue_url": "https://github.com/example/repo/issues/9",
        "issue_title": "FYI historical backfill state (fyi-backfill-state)",
        "state": {
            "complete": False,
            "id_from": 1,
            "id_to": 3000,
            "next_id": 2001,
            "batches": [
                {
                    "id_from": "2001",
                    "id_to": "2500",
                    "label": "2001-2500",
                    "status": "merged",
                    "record_count": 2,
                    "worker_run_id": "run-2001",
                }
            ],
            "dispatched": [{"controller_run_id": "controller-1"}],
        },
    }
    monkeypatch.setattr(
        "fyi_archive.backfill_verification.utc_now",
        lambda: datetime(2026, 6, 30, tzinfo=UTC),
    )

    report = build_backfill_verification_report(
        state_info=state_info,
        merged_manifest_path=manifest,
    )

    assert report["github_actions"]["published_request_ids"] == 3
    assert report["github_actions"]["published_ids_outside_controller_merged_ranges"] == 1
    assert report["github_actions"]["published_ids_outside_controller_sample"] == [10]
    assert report["comparison"]["captured_matches_merged"] is False
    assert report["comparison"]["controller_coverage_verified"] is True
    assert report["comparison"]["published_ids_match_controller_ranges"] is False
    assert report["comparison"]["fully_verified"] is False


def test_remote_huggingface_record_count_downloads_manifest(tmp_path: Path, monkeypatch) -> None:
    snapshot = tmp_path / "snapshot"
    manifest = snapshot / "manifests" / "latest_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"meta": {"record_count": 5}, "requests": []}\n', encoding="utf-8")
    calls: dict[str, object] = {}

    def fake_snapshot_download(**kwargs: object) -> str:
        calls.update(kwargs)
        return str(snapshot)

    monkeypatch.setattr(
        "fyi_archive.backfill_verification.snapshot_download",
        fake_snapshot_download,
    )

    info = remote_huggingface_record_count(
        repo_id="owner/dataset",
        token="hf-token",
        revision="abc123",
    )

    assert info["record_count"] == 5
    assert info["repo_id"] == "owner/dataset"
    assert calls["allow_patterns"] == "manifests/latest_manifest.json"


@respx.mock
def test_remote_zenodo_record_count_downloads_manifest() -> None:
    respx.get("https://zenodo.example/api/deposit/depositions/42").mock(
        return_value=Response(
            200,
            json={
                "doi": "10.5281/zenodo.42",
                "files": [
                    {
                        "filename": "latest_manifest.json",
                        "links": {"download": "https://zenodo.example/file"},
                    }
                ],
            },
        ),
    )
    respx.get("https://zenodo.example/file").mock(
        return_value=Response(200, json={"meta": {"record_count": 4}})
    )

    info = remote_zenodo_record_count(
        token="zenodo-token",
        deposition_id=42,
        api_url="https://zenodo.example/api",
    )

    assert info["record_count"] == 4
    assert info["doi"] == "10.5281/zenodo.42"
