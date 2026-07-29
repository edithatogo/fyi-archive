from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from fyi_archive.wayback_evidence import find_site_count, verify_site_artifact


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


def _mutate_retrieval(root: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    path = root / "retrieval-00.json"
    payload = json.loads(path.read_text())
    mutate(payload)
    _write_json(path, payload)
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifacts"][0]["evidence_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    _write_json(manifest_path, manifest)


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


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value["pagination"].update(mode="offset"), "pagination mode"),
        (lambda value: value.update(artifacts=[]), "no artifacts"),
        (lambda value: value.update(artifacts=["bad"]), "not an object"),
        (lambda value: value.update(complete=True), "manifest completeness"),
    ],
)
def test_rejects_invalid_manifest_states(
    tmp_path: Path, mutation: Callable[[dict[str, Any]], None], message: str
) -> None:
    _artifact(tmp_path, complete=False)
    path = tmp_path / "manifest.json"
    payload = json.loads(path.read_text())
    mutation(payload)
    _write_json(path, payload)

    with pytest.raises(RuntimeError, match=message):
        verify_site_artifact(tmp_path)


def test_rejects_absolute_artifact_path(tmp_path: Path) -> None:
    _artifact(tmp_path, complete=False)
    path = tmp_path / "manifest.json"
    payload = json.loads(path.read_text())
    payload["artifacts"][0]["evidence_path"] = str((tmp_path / "absolute.json").resolve())
    _write_json(path, payload)
    with pytest.raises(RuntimeError, match="must be relative"):
        verify_site_artifact(tmp_path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update(pagination_mode="offset"), "pagination mode"),
        (lambda value: value.update(checkpoint=None), "no retrieval checkpoint"),
        (
            lambda value: value["checkpoint"].update(config_sha256="bad"),
            "configuration hash",
        ),
        (lambda value: value.update(record_count=2), "record counts"),
        (lambda value: value.update(retrieval_status="unknown"), "neither complete nor failed"),
        (
            lambda value: value.update(response_sha256="failed-open"),
            "failed-open",
        ),
        (
            lambda value: value["checkpoint"].update(next_resume_key="other"),
            "invalid resume state",
        ),
        (
            lambda value: value["checkpoint"].update(resumable=False),
            "invalid resume state",
        ),
    ],
)
def test_rejects_invalid_retrieval_states(
    tmp_path: Path, mutation: Callable[[dict[str, Any]], None], message: str
) -> None:
    _artifact(tmp_path, complete=False)
    _mutate_retrieval(tmp_path, mutation)
    with pytest.raises(RuntimeError, match=message):
        verify_site_artifact(tmp_path)


@pytest.mark.parametrize(
    ("target", "field", "value", "message"),
    [
        ("checkpoint", "completed_pages", 2, "page count"),
        ("checkpoint", "record_count", 2, "record counts"),
        ("page", "page", 1, "indices"),
        ("page", "fingerprint", "bad", "fingerprint"),
    ],
)
def test_rejects_invalid_checkpoint_or_page(
    tmp_path: Path, target: str, field: str, value: object, message: str
) -> None:
    _artifact(tmp_path, complete=False)
    path = (
        tmp_path / "cdx-00.pages" / "checkpoint.json"
        if target == "checkpoint"
        else tmp_path / "cdx-00.pages" / "page-000000.json"
    )
    payload = json.loads(path.read_text())
    payload[field] = value
    _write_json(path, payload)
    with pytest.raises(RuntimeError, match=message):
        verify_site_artifact(tmp_path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update(response_sha256="bad"), "response hash"),
        (
            lambda value: value["checkpoint"].update(resumable=True),
            "complete retrieval is resumable",
        ),
        (
            lambda value: value["checkpoint"].update(next_resume_key="cursor"),
            "complete retrieval retains a cursor",
        ),
    ],
)
def test_rejects_invalid_complete_retrieval(
    tmp_path: Path, mutation: Callable[[dict[str, Any]], None], message: str
) -> None:
    _artifact(tmp_path, complete=True)
    _mutate_retrieval(tmp_path, mutation)
    with pytest.raises(RuntimeError, match=message):
        verify_site_artifact(tmp_path)


def test_find_site_count_handles_missing_single_and_duplicate(tmp_path: Path) -> None:
    assert find_site_count(tmp_path, "example") is None
    first = tmp_path / "first"
    _artifact(first, complete=False)
    assert find_site_count(tmp_path, "example") == 1
    _artifact(tmp_path / "second", complete=False)
    with pytest.raises(RuntimeError, match="multiple manifests"):
        find_site_count(tmp_path, "example")
