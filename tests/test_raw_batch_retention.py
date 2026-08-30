"""Raw restoration must reject metadata-only or corrupted capture packages."""

import hashlib
import io
import json
import shutil
from pathlib import Path

import pytest
from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import WARCWriter

from fyi_archive.raw_batch_retention import build_raw_inventory, verify_raw_inventory


def make_capture(root: Path) -> None:
    request = root / "data/raw/requests/example/1"
    request.mkdir(parents=True)
    (request / "request.json").write_text('{"id":1}', encoding="utf-8")
    html = b"<html>public fixture</html>"
    (request / "page.html").write_bytes(html)
    attachment = root / "data/attachments/object"
    attachment.parent.mkdir(parents=True)
    attachment.write_bytes(b"fixture attachment")
    warc = root / "data/warc/capture.warc.gz"
    warc.parent.mkdir(parents=True)
    resources = []
    with warc.open("wb") as stream:
        writer = WARCWriter(stream, gzip=True)
        for kind, payload, path in [
            ("json", b'{"id": 1}', None),
            ("html", html, None),
            ("attachment", attachment.read_bytes(), "data/attachments/object"),
        ]:
            record = writer.create_warc_record(
                "https://example.org/" + kind,
                "response",
                payload=io.BytesIO(payload),
                http_headers=StatusAndHeaders("200 OK", [], protocol="HTTP/1.1"),
            )
            writer.write_record(record)
            resources.append({
                "kind": kind,
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "path": path,
                "warc_record_id": record.rec_headers.get_header("WARC-Record-ID"),
            })
    (request / "snapshot_meta.json").write_text(
        json.dumps({"resources": resources}), encoding="utf-8"
    )


def test_exact_raw_inventory_survives_clean_directory_restore(tmp_path: Path) -> None:
    make_capture(tmp_path / "capture")
    expected = build_raw_inventory(tmp_path / "capture", expected_requests=1)
    shutil.copytree(tmp_path / "capture", tmp_path / "restored")
    verify_raw_inventory(tmp_path / "restored", expected)
    assert expected["request_count"] == 1
    assert expected["warc_resource_count"] == 3
    assert expected["public_publication_verified"] is False
    (tmp_path / "restored/data/raw/requests/example/1/page.html").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match=r"raw|WARC|retained"):
        verify_raw_inventory(tmp_path / "restored", expected)


@pytest.mark.parametrize(
    "missing",
    [
        "data/warc/capture.warc.gz",
        "data/attachments/object",
        "data/raw/requests/example/1/page.html",
    ],
)
def test_missing_raw_object_fails(tmp_path: Path, missing: str) -> None:
    make_capture(tmp_path)
    (tmp_path / missing).unlink()
    with pytest.raises(ValueError, match=r"raw|WARC|retained"):
        build_raw_inventory(tmp_path, expected_requests=1)


def test_metadata_only_and_wrong_request_count_fail(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"raw|WARC|retained"):
        build_raw_inventory(tmp_path, expected_requests=1)
    make_capture(tmp_path)
    with pytest.raises(ValueError, match=r"raw|WARC|retained"):
        build_raw_inventory(tmp_path, expected_requests=2)


def test_symlink_cannot_enter_retained_package(tmp_path: Path) -> None:
    make_capture(tmp_path)
    (tmp_path / "data/link").symlink_to(tmp_path / "data/attachments/object")
    with pytest.raises(ValueError, match="unsafe"):
        build_raw_inventory(tmp_path, expected_requests=1)


def test_workflow_restores_raw_before_crediting_progress() -> None:
    workflow = (
        Path(__file__).parents[1] / ".github/workflows/nz_real_backfill_batch.yml"
    ).read_text(encoding="utf-8")
    assert "verify_raw_batch.py build" in workflow
    assert "verify_raw_batch.py verify" in workflow
    assert workflow.index("verify_raw_batch.py verify") < workflow.index(
        "- name: Complete durable NZ range receipt"
    )
    assert "data/\n            dist/site_snapshots/" in workflow
    assert "raw_package_manifest_sha256" in workflow
    assert "merge-multiple: true" in workflow
    assert "--fyi-cli-version 1.2.0" not in workflow


def test_attachment_path_escape_is_rejected(tmp_path: Path) -> None:
    make_capture(tmp_path)
    metadata = tmp_path / "data/raw/requests/example/1/snapshot_meta.json"
    document = json.loads(metadata.read_text(encoding="utf-8"))
    document["resources"][-1]["path"] = "../outside"
    metadata.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="unsafe attachment"):
        build_raw_inventory(tmp_path, expected_requests=1)


def test_missing_response_kind_and_wrong_receipt_fail(tmp_path: Path) -> None:
    make_capture(tmp_path)
    expected = build_raw_inventory(tmp_path, expected_requests=1)
    expected["total_bytes"] += 1
    with pytest.raises(ValueError, match="differs"):
        verify_raw_inventory(tmp_path, expected)
    metadata = tmp_path / "data/raw/requests/example/1/snapshot_meta.json"
    document = json.loads(metadata.read_text(encoding="utf-8"))
    document["resources"] = document["resources"][1:]
    metadata.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="JSON and HTML"):
        build_raw_inventory(tmp_path, expected_requests=1)


def test_retention_file_budget_is_enforced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_capture(tmp_path)
    monkeypatch.setattr("fyi_archive.raw_batch_retention.MAX_RAW_FILES", 1)
    with pytest.raises(ValueError, match="budget"):
        build_raw_inventory(tmp_path, expected_requests=1)
