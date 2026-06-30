"""Tests for the backfill verification report."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import respx
from httpx import Response
from typer.testing import CliRunner

from fyi_archive.cli import app
from fyi_archive.backfill_verification import remote_zenodo_record_count

runner = CliRunner()


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


def test_backfill_report_cli_allows_dry_run_without_full_verification(tmp_path: Path, monkeypatch) -> None:
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
