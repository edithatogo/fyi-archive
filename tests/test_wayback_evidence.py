from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from fyi_archive.wayback_evidence import verify_site_artifact


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _artifact(root: Path, *, complete: bool, resumable: bool = True) -> None:
    rows = [["https://example.test/request/1"]] if complete or resumable else []
    fingerprint = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    config = {
        "url_pattern": "example.test/request/*",
        "instance_id": "example",
        "host": "example.test",
        "page_size": 1000,
        "capture_mode": "url_index",
        "pagination_mode": "resume_key",
        "endpoint": "https://web.archive.org/cdx/search/cdx",
    }
    config_sha256 = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    next_key = "cursor" if not complete and resumable else None
    completed_pages = int(bool(rows))
    checkpoint = {
        "schema_version": "2.0",
        "config_sha256": config_sha256,
        "completed_pages": completed_pages,
        "next_page": completed_pages,
        "next_resume_key": next_key,
        "record_count": len(rows),
    }
    if rows:
        _write_json(
            root / "cdx-00.pages" / "page-000000.json",
            {
                "page": 0,
                "header": ["original"],
                "rows": rows,
                "fingerprint": fingerprint,
            },
        )
    _write_json(root / "cdx-00.pages" / "checkpoint.json", checkpoint)
    export = [["original"], *rows]
    export_raw = json.dumps(export, indent=2) + "\n"
    if complete:
        (root / "cdx-00.json").write_bytes(export_raw.encode())
    retrieval = {
        "instance_id": "example",
        "host": "example.test",
        "endpoint": config["endpoint"],
        "url_pattern": config["url_pattern"],
        "capture_mode": "url_index",
        "pagination_mode": "resume_key",
        "page_size": 1000,
        "retrieval_status": "complete" if complete else "failed",
        "pagination_complete": complete,
        "record_count": len(rows),
        "response_sha256": hashlib.sha256(export_raw.encode()).hexdigest() if complete else None,
        "checkpoint": {
            "config_sha256": config_sha256,
            "completed_pages": completed_pages,
            "next_resume_key": next_key,
            "resumable": resumable and not complete,
        },
    }
    _write_json(root / "retrieval-00.json", retrieval)
    manifest_artifact = {
        "path": "cdx-00.json" if complete else None,
        "evidence_path": "retrieval-00.json",
        "pagination_complete": complete,
        "record_count": len(rows),
        "evidence_sha256": hashlib.sha256((root / "retrieval-00.json").read_bytes()).hexdigest(),
    }
    if complete:
        manifest_artifact["sha256"] = hashlib.sha256(export_raw.encode()).hexdigest()
    _write_json(
        root / "manifest.json",
        {
            "site_id": "example",
            "country": "XX",
            "complete": complete,
            "pagination": {"mode": "resume_key"},
            "resume": {"source_run_id": "123"},
            "artifacts": [manifest_artifact],
        },
    )


@pytest.mark.parametrize("complete", [False, True])
def test_verifies_complete_and_resumable_artifacts(tmp_path: Path, complete: bool) -> None:
    _artifact(tmp_path, complete=complete)

    report = verify_site_artifact(tmp_path)

    assert report["complete"] is complete
    assert report["resumable"] is not complete
    assert report["record_count"] == 1
    cursor_hash = report["retrievals"][0]["next_resume_key_sha256"]
    assert (cursor_hash is None) is complete


def test_rejects_tampered_page(tmp_path: Path) -> None:
    _artifact(tmp_path, complete=False)
    page = tmp_path / "cdx-00.pages" / "page-000000.json"
    payload = json.loads(page.read_text())
    payload["rows"].append(["tampered"])
    _write_json(page, payload)

    with pytest.raises(RuntimeError, match="fingerprint"):
        verify_site_artifact(tmp_path)


def test_accepts_zero_progress_fail_closed_artifact(tmp_path: Path) -> None:
    _artifact(tmp_path, complete=False, resumable=False)

    report = verify_site_artifact(tmp_path)

    assert report["complete"] is False
    assert report["resumable"] is False
    assert report["record_count"] == 0


def test_rejects_manifest_paths_outside_artifact_root(tmp_path: Path) -> None:
    _artifact(tmp_path, complete=False)
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifacts"][0]["evidence_path"] = "../outside.json"
    _write_json(manifest_path, manifest)

    with pytest.raises(RuntimeError, match="escapes"):
        verify_site_artifact(tmp_path)
