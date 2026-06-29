"""Tests for prospective sync orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import pytest

from fyi_archive.sync import load_sync_state, run_sync, write_sync_health

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


def test_write_sync_health(tmp_path: Path) -> None:
    health_path = tmp_path / "conductor" / "archive_health.json"

    write_sync_health(health_path, {"record_count": 3, "verified": True})

    health = json.loads(health_path.read_text(encoding="utf-8"))
    assert health["sync"]["record_count"] == 3
    assert health["sync"]["verified"] is True
