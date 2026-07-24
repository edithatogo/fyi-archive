"""Tests for manifest assembly."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
from typer.testing import CliRunner

from fyi_archive.cli import app
from fyi_archive.manifest import assemble_manifest, merge_manifests, validate_manifest


def write_record(path: Path, request_id: int, authority: str = "Ministry") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "request_id": request_id,
                "url_title": f"request-{request_id}",
                "title": f"Request {request_id}",
                "authority": authority,
            },
        ),
        encoding="utf-8",
    )


def test_assemble_manifest_writes_json_parquet_and_authorities(tmp_path: Path) -> None:
    derived = tmp_path / "derived"
    write_record(derived / "1.json", 1, "A")
    write_record(derived / "2.json", 2, "B")

    manifest_path = tmp_path / "manifests/latest_manifest.json"
    parquet_path = tmp_path / "manifests/latest_manifest.parquet"
    authorities_path = tmp_path / "manifests/authorities.json"

    manifest = assemble_manifest(
        derived_dir=derived,
        manifest_path=manifest_path,
        parquet_path=parquet_path,
        authorities_path=authorities_path,
        fyi_cli_version="1.0.0",
    )

    validate_manifest(manifest)
    assert manifest["meta"]["record_count"] == 2
    assert manifest["meta"]["instance_id"] == "nz-fyi"
    assert manifest["meta"]["source"] == "https://fyi.org.nz/"
    assert json.loads(authorities_path.read_text(encoding="utf-8")) == {"authorities": ["A", "B"]}
    assert pl.read_parquet(parquet_path).height == 2


def test_assemble_manifest_loads_fyi_cli_request_directory(tmp_path: Path) -> None:
    request_dir = tmp_path / "derived" / "ministry_of_health" / "20000"
    request_dir.mkdir(parents=True)
    (request_dir / "request.json").write_text(
        json.dumps(
            {
                "id": 20000,
                "url_title": "request-20000",
                "title": "Live request",
                "authority": {"url_name": "ministry_of_health", "name": "Ministry of Health"},
                "state": "successful",
            },
        ),
        encoding="utf-8",
    )
    (request_dir / "page.html").write_text("<html></html>", encoding="utf-8")
    (request_dir / "attachments.json").write_text("[]", encoding="utf-8")
    (request_dir / "snapshot_meta.json").write_text(
        json.dumps({"resources": [{"warc_record_id": "<urn:uuid:test>"}]}),
        encoding="utf-8",
    )

    manifest = assemble_manifest(
        derived_dir=tmp_path / "derived",
        manifest_path=tmp_path / "manifest.json",
        parquet_path=tmp_path / "manifest.parquet",
        authorities_path=tmp_path / "authorities.json",
        fyi_cli_version="1.0.0",
    )

    record = manifest["requests"][0]
    assert record["request_id"] == 20000
    assert record["authority"] == "ministry_of_health"
    assert record["html_captured"] is True
    assert record["warc_record_ids"] == ["<urn:uuid:test>"]


def test_assemble_manifest_uses_numeric_directory_id_when_payload_omits_id(tmp_path: Path) -> None:
    request_dir = tmp_path / "derived" / "unknown" / "7"
    request_dir.mkdir(parents=True)
    (request_dir / "request.json").write_text(
        json.dumps({"url_title": "request-7", "title": "Captured"}), encoding="utf-8"
    )
    manifest = assemble_manifest(
        derived_dir=tmp_path / "derived",
        manifest_path=tmp_path / "manifest.json",
        parquet_path=tmp_path / "manifest.parquet",
        authorities_path=tmp_path / "authorities.json",
        fyi_cli_version="1.2.0",
    )
    assert manifest["requests"][0]["request_id"] == 7


def test_manifest_cli_build(tmp_path: Path) -> None:
    derived = tmp_path / "derived"
    write_record(derived / "1.json", 1)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "manifest",
            "build",
            "--derived-dir",
            str(derived),
            "--manifest-path",
            str(tmp_path / "latest_manifest.json"),
            "--parquet-path",
            str(tmp_path / "latest_manifest.parquet"),
            "--authorities-path",
            str(tmp_path / "authorities.json"),
            "--fyi-cli-version",
            "1.0.0",
        ],
    )

    assert result.exit_code == 0
    assert '"record_count": 1' in result.stdout


def test_merge_manifests_dedupes_by_request_id(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    write_record(first_dir / "1.json", 1, "A")
    write_record(first_dir / "2.json", 2, "Old")
    write_record(second_dir / "2.json", 2, "New")
    write_record(second_dir / "3.json", 3, "C")
    first_manifest = assemble_manifest(
        derived_dir=first_dir,
        manifest_path=tmp_path / "first.json",
        parquet_path=tmp_path / "first.parquet",
        authorities_path=tmp_path / "first_authorities.json",
        fyi_cli_version="1.0.0",
    )
    second_manifest = assemble_manifest(
        derived_dir=second_dir,
        manifest_path=tmp_path / "second.json",
        parquet_path=tmp_path / "second.parquet",
        authorities_path=tmp_path / "second_authorities.json",
        fyi_cli_version="1.0.0",
    )

    merged = merge_manifests(
        manifest_paths=[tmp_path / "first.json", tmp_path / "second.json"],
        manifest_path=tmp_path / "merged.json",
        parquet_path=tmp_path / "merged.parquet",
        authorities_path=tmp_path / "merged_authorities.json",
        fyi_cli_version="1.0.0",
    )

    assert first_manifest["meta"]["record_count"] == 2
    assert second_manifest["meta"]["record_count"] == 2
    assert [record["request_id"] for record in merged["requests"]] == [1, 2, 3]
    assert merged["requests"][1]["authority"] == "New"
    assert pl.read_parquet(tmp_path / "merged.parquet").height == 3


def test_manifest_cli_merge(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    write_record(first_dir / "1.json", 1)
    write_record(second_dir / "2.json", 2)
    assemble_manifest(
        derived_dir=first_dir,
        manifest_path=tmp_path / "first.json",
        parquet_path=tmp_path / "first.parquet",
        authorities_path=tmp_path / "first_authorities.json",
        fyi_cli_version="1.0.0",
    )
    assemble_manifest(
        derived_dir=second_dir,
        manifest_path=tmp_path / "second.json",
        parquet_path=tmp_path / "second.parquet",
        authorities_path=tmp_path / "second_authorities.json",
        fyi_cli_version="1.0.0",
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "manifest",
            "merge",
            "--input-manifest",
            str(tmp_path / "first.json"),
            "--input-manifest",
            str(tmp_path / "second.json"),
            "--manifest-path",
            str(tmp_path / "merged.json"),
            "--parquet-path",
            str(tmp_path / "merged.parquet"),
            "--authorities-path",
            str(tmp_path / "merged_authorities.json"),
            "--fyi-cli-version",
            "1.0.0",
        ],
    )

    assert result.exit_code == 0
    assert '"record_count": 2' in result.stdout


def test_manifest_rejects_cross_jurisdiction_record() -> None:
    manifest = {
        "meta": {
            "source": "https://fyi.org.nz/",
            "instance_id": "nz-fyi",
            "jurisdiction": "NZ",
            "record_count": 1,
        },
        "requests": [{"request_id": 1, "content_sha256": "a" * 64, "jurisdiction": "NSW"}],
    }
    try:
        validate_manifest(manifest)
    except ValueError as error:
        assert "jurisdiction" in str(error)
    else:
        raise AssertionError("cross-jurisdiction record was accepted")
