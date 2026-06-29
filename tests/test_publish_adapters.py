"""Tests for publish adapters."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import polars as pl
import pytest
import respx
from httpx import Response

from fyi_archive.publish.export import build_duckdb_export
from fyi_archive.publish.hf_publish import sha256_file, verify_remote_manifest
from fyi_archive.publish.metadata import write_metadata
from fyi_archive.publish.osf_publish import create_component, create_project
from fyi_archive.publish.zenodo_publish import create_draft, publish_draft, upload_file


def test_verify_remote_manifest_matches_snapshot(tmp_path: Path, monkeypatch) -> None:
    local_manifest = tmp_path / "local.json"
    local_manifest.write_text('{"ok": true}\n', encoding="utf-8")
    snapshot = tmp_path / "snapshot"
    remote_manifest = snapshot / "manifests/latest_manifest.json"
    remote_manifest.parent.mkdir(parents=True)
    remote_manifest.write_text(local_manifest.read_text(encoding="utf-8"), encoding="utf-8")

    def fake_snapshot_download(**kwargs) -> str:
        assert kwargs["repo_id"] == "owner/dataset"
        return str(snapshot)

    monkeypatch.setattr("fyi_archive.publish.hf_publish.snapshot_download", fake_snapshot_download)

    assert verify_remote_manifest(repo_id="owner/dataset", local_manifest=local_manifest)
    assert sha256_file(local_manifest) == sha256_file(remote_manifest)


@respx.mock
def test_zenodo_create_upload_and_publish_are_draft_first(tmp_path: Path) -> None:
    respx.post("https://zenodo.example/api/deposit/depositions").mock(
        return_value=Response(201, json={"id": 1, "links": {"bucket": "https://bucket.example/1"}}),
    )
    respx.put("https://bucket.example/1/file.txt").mock(
        return_value=Response(200, json={"key": "file.txt"})
    )
    respx.post("https://zenodo.example/api/deposit/depositions/1/actions/publish").mock(
        return_value=Response(202, json={"doi": "10.5281/zenodo.1"}),
    )
    file_path = tmp_path / "file.txt"
    file_path.write_text("content", encoding="utf-8")

    draft = create_draft(
        token="token", metadata={"title": "Dataset"}, api_url="https://zenodo.example/api"
    )
    uploaded = upload_file(token="token", bucket_url=draft["links"]["bucket"], path=file_path)

    with pytest.raises(ValueError, match="Publishing requires"):
        publish_draft(
            token="token",
            deposition_id=1,
            confirm="wrong",
            api_url="https://zenodo.example/api",
        )

    published = publish_draft(
        token="token",
        deposition_id=1,
        confirm="publish-zenodo-doi",
        api_url="https://zenodo.example/api",
    )

    assert uploaded["key"] == "file.txt"
    assert published["doi"] == "10.5281/zenodo.1"


def test_metadata_and_duckdb_export(tmp_path: Path) -> None:
    manifest = {
        "meta": {
            "source": "https://fyi.org.nz/",
            "version": "0.1.0",
            "record_count": 1,
        },
        "requests": [{"request_id": 1, "url_title": "one"}],
    }
    manifest_path = tmp_path / "manifests/latest_manifest.json"
    parquet_path = tmp_path / "manifests/latest_manifest.parquet"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    pl.DataFrame(manifest["requests"]).write_parquet(parquet_path)

    metadata_dir = tmp_path / "metadata"
    write_metadata(manifest_path, metadata_dir)

    db_path = tmp_path / "dist/fyi_archive.duckdb"
    build_duckdb_export(manifest_parquet=parquet_path, output_path=db_path)

    assert (metadata_dir / "croissant.jsonld").exists()
    assert (metadata_dir / "frictionless.json").exists()
    assert (metadata_dir / "schema.org.jsonld").exists()
    with duckdb.connect(str(db_path), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM requests").fetchone() == (1,)


@respx.mock
def test_osf_create_project_and_component() -> None:
    respx.post("https://osf.example/v2/nodes/").mock(
        return_value=Response(201, json={"data": {"id": "abc123"}}),
    )
    respx.post("https://osf.example/v2/nodes/abc123/children/").mock(
        return_value=Response(201, json={"data": {"id": "child123"}}),
    )

    project = create_project(token="token", title="fyi-archive", api_url="https://osf.example/v2")
    component = create_component(
        token="token",
        parent_id=project["data"]["id"],
        title="Hugging Face mirror",
        api_url="https://osf.example/v2",
    )

    assert component["data"]["id"] == "child123"
