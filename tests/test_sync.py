"""Tests for prospective sync orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import pytest

from fyi_archive.sync import load_sync_state, restore_hf_dataset, run_sync, write_sync_health

HEX = "a" * 64


class SyncPaths(TypedDict):
    """Path bundle expected by run_sync."""

    state_path: Path
    derived_dir: Path
    manifest_path: Path
    parquet_path: Path
    authorities_path: Path
    changes_path: Path


def sync_paths(tmp_path: Path) -> SyncPaths:
    """Return standard sync paths under a temporary root."""
    return {
        "state_path": tmp_path / "data" / "_state" / "sync_state.json",
        "derived_dir": tmp_path / "data" / "derived" / "requests",
        "manifest_path": tmp_path / "manifests" / "latest_manifest.json",
        "parquet_path": tmp_path / "manifests" / "latest_manifest.parquet",
        "authorities_path": tmp_path / "manifests" / "authorities.json",
        "changes_path": tmp_path / "manifests" / "latest_changes.json",
    }


def write_changes(path: Path, *, added: list[dict[str, object]] | None = None) -> None:
    """Write a valid changes document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "meta": {
                    "generated_at": "2026-01-01T00:00:00+00:00",
                    "since": None,
                    "version": "0.1.0",
                },
                "added": added or [],
                "updated": [],
                "removed": [],
            },
        ),
        encoding="utf-8",
    )


def test_run_sync_empty_diff_is_idempotent(tmp_path: Path) -> None:
    paths = sync_paths(tmp_path)
    write_changes(paths["changes_path"])

    first = run_sync(**paths, fyi_cli_version="1.0.0", dry_run=True)
    second = run_sync(**paths, fyi_cli_version="1.0.0", dry_run=True)

    assert first["record_count"] == 0
    assert second["record_count"] == 0
    assert load_sync_state(paths["state_path"]).record_count == 0


def test_run_sync_materializes_new_records(tmp_path: Path) -> None:
    paths = sync_paths(tmp_path)
    write_changes(
        paths["changes_path"],
        added=[{"request_id": 123, "url_title": "new-request", "content_sha256": HEX}],
    )

    summary = run_sync(**paths, fyi_cli_version="1.0.0", dry_run=True)
    manifest = json.loads(paths["manifest_path"].read_text(encoding="utf-8"))

    assert summary["materialized_records"] == 1
    assert manifest["meta"]["record_count"] == 1
    assert manifest["requests"][0]["request_id"] == 123
    assert manifest["requests"][0]["content_sha256"] == HEX


def test_run_sync_does_not_advance_state_on_verify_failure(tmp_path: Path) -> None:
    paths = sync_paths(tmp_path)
    write_changes(
        paths["changes_path"],
        added=[{"request_id": 123, "url_title": "new-request", "content_sha256": HEX}],
    )

    with pytest.raises(RuntimeError, match="Remote manifest SHA-256 verification failed"):
        run_sync(
            **paths,
            fyi_cli_version="1.0.0",
            dry_run=True,
            hf_repo_id="edithatogo/fyi-archive-nz",
            verify_remote=lambda **_: False,
        )

    assert not paths["state_path"].exists()


def test_restore_hf_dataset_copies_manifest_and_requests(tmp_path: Path, monkeypatch) -> None:
    snapshot = tmp_path / "snapshot"
    restored_manifest = snapshot / "manifests" / "latest_manifest.json"
    restored_request = snapshot / "data" / "raw" / "requests" / "authority" / "1" / "request.json"
    restored_manifest.parent.mkdir(parents=True)
    restored_request.parent.mkdir(parents=True)
    restored_manifest.write_text('{"meta": {"record_count": 1}, "requests": []}\n', encoding="utf-8")
    restored_request.write_text('{"request_id": 1}\n', encoding="utf-8")

    def fake_snapshot_download(**kwargs) -> str:
        assert kwargs["repo_id"] == "owner/dataset"
        assert "manifests/*" in kwargs["allow_patterns"]
        return str(snapshot)

    monkeypatch.setattr("fyi_archive.sync.snapshot_download", fake_snapshot_download)

    restore_hf_dataset(
        repo_id="owner/dataset",
        token="token",
        manifest_dir=tmp_path / "manifests",
        derived_dir=tmp_path / "data" / "raw" / "requests",
    )

    assert (tmp_path / "manifests" / "latest_manifest.json").exists()
    assert (tmp_path / "data" / "raw" / "requests" / "authority" / "1" / "request.json").exists()


def test_run_sync_live_empty_diff_restores_before_verify(tmp_path: Path, monkeypatch) -> None:
    paths = sync_paths(tmp_path)
    restored_manifest = {
        "meta": {"generated_at": "2026-01-01T00:00:00+00:00", "record_count": 1},
        "requests": [{"request_id": 123, "content_sha256": HEX}],
    }

    def fake_restore_hf_dataset(**kwargs) -> None:
        paths["manifest_path"].parent.mkdir(parents=True, exist_ok=True)
        paths["manifest_path"].write_text(json.dumps(restored_manifest), encoding="utf-8")
        request_dir = paths["derived_dir"] / "authority" / "123"
        request_dir.mkdir(parents=True)
        (request_dir / "request.json").write_text(
            json.dumps({"request_id": 123, "content_sha256": HEX}),
            encoding="utf-8",
        )

    def fake_run_fyi_cli_diff(**kwargs) -> None:
        write_changes(paths["changes_path"])

    monkeypatch.setattr("fyi_archive.sync.restore_hf_dataset", fake_restore_hf_dataset)
    monkeypatch.setattr("fyi_archive.sync.run_fyi_cli_diff", fake_run_fyi_cli_diff)

    summary = run_sync(
        **paths,
        fyi_cli_version="1.0.0",
        dry_run=False,
        hf_repo_id="owner/dataset",
        hf_token="token",
        verify_remote=lambda **kwargs: kwargs["local_manifest"] == paths["manifest_path"],
    )

    assert summary["record_count"] == 1
    assert summary["materialized_records"] == 0
    assert load_sync_state(paths["state_path"]).record_count == 1


def test_write_sync_health(tmp_path: Path) -> None:
    health_path = tmp_path / "conductor" / "archive_health.json"

    write_sync_health(health_path, {"record_count": 3, "verified": True})

    health = json.loads(health_path.read_text(encoding="utf-8"))
    assert health["sync"]["record_count"] == 3
    assert health["sync"]["verified"] is True
