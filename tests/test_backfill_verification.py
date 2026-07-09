"""Tests for the backfill verification report."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import respx
from httpx import Response
from typer.testing import CliRunner

from fyi_archive import backfill_verification
from fyi_archive.backfill_state_codec import state_body_from_state
from fyi_archive.backfill_verification import remote_zenodo_record_count
from fyi_archive.cli import app

runner = CliRunner()


def test_gh_json_parses_stdout(monkeypatch) -> None:
    completed = subprocess.CompletedProcess(args=["gh"], returncode=0, stdout='{"ok": true}\n')
    monkeypatch.setattr(
        backfill_verification.subprocess,
        "run",
        lambda *args, **kwargs: completed,
    )

    assert backfill_verification.gh_json(["status"]) == {"ok": True}


def test_load_controller_state_falls_back_to_all_issues(monkeypatch) -> None:
    calls = iter(
        [
            [],
            [
                {
                    "number": 9,
                    "url": "https://github.com/example/repo/issues/9",
                    "title": "FYI historical backfill state (fyi-backfill-state)",
                }
            ],
            {
                "body": json.dumps({"next_id": 4, "batches": [], "dispatched": []}),
                "number": 9,
                "title": "FYI historical backfill state (fyi-backfill-state)",
                "url": "https://github.com/example/repo/issues/9",
            },
        ]
    )
    monkeypatch.setattr(backfill_verification, "gh_json", lambda args: next(calls))

    state_info = backfill_verification.load_controller_state(
        repo="example/repo",
        state_label="fyi-backfill-state",
    )

    assert state_info["issue_number"] == 9
    assert state_info["issue_url"] == "https://github.com/example/repo/issues/9"
    assert state_info["state"]["next_id"] == 4


def test_load_controller_state_rejects_invalid_body(monkeypatch) -> None:
    monkeypatch.setattr(
        backfill_verification,
        "gh_json",
        lambda args: {
            "body": "not-json",
            "number": 9,
            "title": "FYI historical backfill state (fyi-backfill-state)",
            "url": "https://github.com/example/repo/issues/9",
        },
    )

    try:
        backfill_verification.load_controller_state(
            repo="example/repo",
            state_label="fyi-backfill-state",
            issue_number=9,
        )
    except ValueError as exc:
        assert "does not contain JSON state" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_load_controller_state_prefers_local_snapshot(tmp_path: Path, monkeypatch) -> None:
    snapshot = tmp_path / "versions" / "latest_backfill_controller_state.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text(
        json.dumps(
            {
                "issue_number": 9,
                "issue_url": "https://github.com/example/repo/issues/9",
                "issue_title": "FYI historical backfill state (fyi-backfill-state)",
                "state_label": "fyi-backfill-state",
                "state": {"next_id": 4, "batches": [], "dispatched": []},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BACKFILL_STATE_SNAPSHOT", str(snapshot))

    state_info = backfill_verification.load_controller_state(
        repo="example/repo",
        state_label="fyi-backfill-state",
    )

    assert state_info["issue_number"] == 9
    assert state_info["state"]["next_id"] == 4


def test_load_controller_state_decodes_compressed_issue_body(monkeypatch) -> None:
    encoded_state = state_body_from_state({"next_id": 4, "batches": [], "dispatched": []})

    monkeypatch.setattr(
        backfill_verification,
        "gh_json",
        lambda args: {
            "body": encoded_state,
            "number": 9,
            "title": "FYI historical backfill state (fyi-backfill-state)",
            "url": "https://github.com/example/repo/issues/9",
        },
    )

    state_info = backfill_verification.load_controller_state(
        repo="example/repo",
        state_label="fyi-backfill-state",
        issue_number=9,
    )

    assert state_info["state"]["next_id"] == 4


def test_remote_huggingface_record_count_uses_downloaded_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    snapshot_path = tmp_path / "snapshot"
    manifest_path = snapshot_path / "manifests/latest_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text('{"meta": {"record_count": 5}}\n', encoding="utf-8")

    monkeypatch.setattr(
        backfill_verification,
        "snapshot_download",
        lambda **kwargs: snapshot_path.as_posix(),
    )
    monkeypatch.setattr(backfill_verification, "sha256_file", lambda path: "abc123")
    monkeypatch.setattr(
        backfill_verification,
        "manifest_record_count",
        lambda path: 5,
    )

    info = backfill_verification.remote_huggingface_record_count(
        repo_id="owner/dataset",
        token="hf-token",
    )

    assert info["manifest_path"].endswith("manifests/latest_manifest.json")
    assert info["manifest_sha256"] == "abc123"
    assert info["record_count"] == 5


def test_remote_zenodo_record_count_requires_manifest_url(monkeypatch) -> None:
    monkeypatch.setattr(
        backfill_verification,
        "get_deposition",
        lambda **kwargs: {"doi": "10.5281/zenodo.42"},
    )
    monkeypatch.setattr(backfill_verification, "deposition_artifacts", lambda deposition: [])

    try:
        backfill_verification.remote_zenodo_record_count(
            token="zenodo-token",
            deposition_id=42,
            api_url="https://zenodo.example/api",
        )
    except ValueError as exc:
        assert "does not expose latest_manifest.json" in str(exc)
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


def test_backfill_verification_helpers_cover_state_loading_and_writers(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("BACKFILL_STATE_SNAPSHOT", raising=False)
    manifest = tmp_path / "manifests/latest_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"meta": {"record_count": 3}, "requests": []}\n', encoding="utf-8")

    controller_state = {
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
    }

    def fake_gh_json(args: list[str]):
        if args[:2] == ["issue", "list"]:
            return [
                {
                    "number": 9,
                    "url": "https://github.com/example/repo/issues/9",
                    "title": "FYI historical backfill state (fyi-backfill-state)",
                }
            ]
        if args[:2] == ["issue", "view"]:
            return {
                "body": json.dumps(controller_state),
                "number": 9,
                "title": "FYI historical backfill state (fyi-backfill-state)",
                "url": "https://github.com/example/repo/issues/9",
            }
        raise AssertionError(f"unexpected gh_json call: {args}")

    monkeypatch.setattr(backfill_verification, "gh_json", fake_gh_json)
    monkeypatch.setattr(
        "fyi_archive.backfill_verification.utc_now",
        lambda: datetime(2026, 6, 30, tzinfo=UTC),
    )

    state_info = backfill_verification.load_controller_state(
        repo="example/repo",
        state_label="fyi-backfill-state",
    )
    report = backfill_verification.build_backfill_verification_report(
        state_info=state_info,
        merged_manifest_path=manifest,
        hf_info={"record_count": 3},
        zenodo_info={"record_count": 3},
    )

    report_path = tmp_path / "dist/backfill_verification.json"
    versions_dir = tmp_path / "versions"
    backfill_verification.write_backfill_report(report_path, report)
    backfill_verification.write_versioned_backfill_report(report=report, output_dir=versions_dir)

    assert state_info["issue_number"] == 9
    assert report["controller"]["pending_batches"] == 0
    assert report["comparison"]["fully_verified"] is True
    assert report_path.exists()
    assert (versions_dir / "latest_backfill_verification.json").exists()
    assert (versions_dir / "2026-06" / "backfill_verification.json").exists()


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


@respx.mock
def test_remote_zenodo_record_count_falls_back_to_published_record_after_doi() -> None:
    respx.get("https://zenodo.example/api/deposit/depositions/42").mock(
        return_value=Response(
            200,
            json={
                "doi": "10.5281/zenodo.42",
                "files": [
                    {
                        "filename": "latest_manifest.json",
                        "links": {
                            "download": "https://zenodo.example/api/records/42/draft/files/latest_manifest.json/content"
                        },
                    }
                ],
            },
        ),
    )
    respx.get(
        "https://zenodo.example/api/records/42/draft/files/latest_manifest.json/content"
    ).mock(return_value=Response(404))
    respx.get("https://zenodo.example/api/records/42/files/latest_manifest.json/content").mock(
        return_value=Response(200, json={"meta": {"record_count": 4}})
    )

    info = remote_zenodo_record_count(
        token="zenodo-token",
        deposition_id=42,
        api_url="https://zenodo.example/api",
    )

    assert info["record_count"] == 4
    assert info["doi"] == "10.5281/zenodo.42"
