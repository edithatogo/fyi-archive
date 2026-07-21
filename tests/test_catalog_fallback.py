"""Tests for verified GitHub catalog recovery."""

from __future__ import annotations

import hashlib
import io
import json
import urllib.error
import zipfile
from pathlib import Path

import pytest

from fyi_archive import catalog_fallback


def test_restore_latest_verified_catalog_accepts_checksum_matched_artifact(
    monkeypatch, tmp_path: Path
) -> None:
    csv_payload = b"url_name,name,url\nagency,Agency,https://example.test/body/agency\n"
    digest = hashlib.sha256(csv_payload).hexdigest()
    payload = {
        "base_url": "https://www.righttoknow.org.au",
        "catalog_url": "https://mirror.example/au.csv",
        "count": 1,
        "bodies": [{"url_name": "agency", "name": "Agency"}],
        "provenance": {"payload_sha256": digest, "row_count": 1},
    }
    source_provenance = {"catalog_url": "https://mirror.example/au.csv", "payload_sha256": digest}
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("discovered_bodies.json", json.dumps(payload))
        bundle.writestr("discovered_bodies.provenance.json", json.dumps(source_provenance))

    monkeypatch.setattr(
        catalog_fallback,
        "_github_json",
        lambda url, token: (
            {"workflow_runs": [{"id": 42}]}
            if url.endswith("/runs?status=success&per_page=20")
            else {
                "artifacts": [
                    {
                        "id": 7,
                        "name": "catalog-42",
                        "archive_download_url": "https://gh.test/artifact",
                    }
                ]
            }
        ),
    )

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return archive.getvalue()

    monkeypatch.setattr(
        catalog_fallback.urllib.request, "urlopen", lambda *args, **kwargs: Response()
    )
    output = tmp_path / "discovered_bodies.json"
    provenance = tmp_path / "discovered_bodies.provenance.json"
    result = catalog_fallback.restore_latest_verified_catalog(
        output_path=output,
        provenance_path=provenance,
        repository="example/archive",
        workflow="rollout.yml",
        token="token",
    )

    assert result["mode"] == "fallback"
    assert result["source_run_id"] == 42
    assert json.loads(output.read_text(encoding="utf-8"))["count"] == 1
    assert json.loads(provenance.read_text(encoding="utf-8"))["catalog_sha256"] == digest


def test_catalog_helpers_fail_closed_and_write_digest(tmp_path: Path) -> None:
    path = tmp_path / "payload.csv"
    path.write_bytes(b"payload")
    sidecar = tmp_path / "nested" / "provenance.json"

    catalog_fallback.write_catalog_provenance(sidecar, {"mode": "live"})

    assert catalog_fallback.catalog_sha256(path) == hashlib.sha256(b"payload").hexdigest()
    assert json.loads(sidecar.read_text(encoding="utf-8"))["mode"] == "live"
    try:
        catalog_fallback.validate_catalog_payload({"bodies": []})
    except catalog_fallback.CatalogArtifactError as error:
        assert "checksum" in str(error)
    else:
        raise AssertionError("missing provenance checksum must fail closed")
    with pytest.raises(catalog_fallback.CatalogArtifactError, match="list of objects"):
        catalog_fallback.validate_catalog_payload(
            {
                "bodies": ["not-an-object"],
                "provenance": {"payload_sha256": "abc"},
            }
        )


def test_restore_requires_token_and_verified_files(monkeypatch, tmp_path: Path) -> None:
    with pytest.raises(catalog_fallback.CatalogArtifactError, match="GITHUB_TOKEN"):
        catalog_fallback.restore_latest_verified_catalog(
            output_path=tmp_path / "catalog.json",
            provenance_path=tmp_path / "provenance.json",
            repository="example/archive",
            workflow="rollout.yml",
            token="",
        )

    monkeypatch.setattr(
        catalog_fallback,
        "_github_json",
        lambda url, token: (
            {"workflow_runs": [{"id": 42}]}
            if url.endswith("/runs?status=success&per_page=20")
            else {"artifacts": []}
        ),
    )
    with pytest.raises(catalog_fallback.CatalogArtifactError, match="no successful"):
        catalog_fallback.restore_latest_verified_catalog(
            output_path=tmp_path / "catalog.json",
            provenance_path=tmp_path / "provenance.json",
            repository="example/archive",
            workflow="rollout.yml",
            token="token",
        )


def test_github_json_and_artifact_schema_failures(monkeypatch, tmp_path: Path) -> None:
    class Response:
        def __init__(self, payload: bytes):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return self.payload

    monkeypatch.setattr(
        catalog_fallback.urllib.request,
        "urlopen",
        lambda *args, **kwargs: Response(b'{"ok": true}'),
    )
    assert catalog_fallback._github_json("https://api.example", "token")["ok"] is True
    monkeypatch.setattr(
        catalog_fallback.urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline")),
    )
    with pytest.raises(catalog_fallback.CatalogArtifactError, match="lookup failed"):
        catalog_fallback._github_json("https://api.example", "token")

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("discovered_bodies.json", json.dumps({"bodies": []}))
    monkeypatch.setattr(
        catalog_fallback,
        "_github_json",
        lambda url, token: (
            {"workflow_runs": [{"id": 42}]}
            if url.endswith("/runs?status=success&per_page=20")
            else {
                "artifacts": [
                    {
                        "id": 7,
                        "name": "catalog-42",
                        "archive_download_url": "https://gh.test/artifact",
                    }
                ]
            }
        ),
    )
    monkeypatch.setattr(
        catalog_fallback.urllib.request,
        "urlopen",
        lambda *args, **kwargs: Response(archive.getvalue()),
    )
    with pytest.raises(catalog_fallback.CatalogArtifactError, match="missing required"):
        catalog_fallback.restore_latest_verified_catalog(
            output_path=tmp_path / "catalog.json",
            provenance_path=tmp_path / "provenance.json",
            repository="example/archive",
            workflow="rollout.yml",
            token="token",
        )


def test_restore_rejects_non_object_and_checksum_mismatch(monkeypatch, tmp_path: Path) -> None:
    class Response:
        def __init__(self, payload: bytes):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return self.payload

    def api(url, token):
        if url.endswith("/runs?status=success&per_page=20"):
            return {"workflow_runs": [{"id": 42}, {"bad": True}]}
        return {
            "artifacts": [
                {"id": 1, "name": "other", "archive_download_url": "https://gh.test/other"},
                {"id": 2, "name": "catalog-42"},
                {"id": 3, "name": "catalog-42", "archive_download_url": "https://gh.test/catalog"},
            ]
        }

    monkeypatch.setattr(catalog_fallback, "_github_json", api)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("discovered_bodies.json", json.dumps(["not-an-object"]))
        bundle.writestr("discovered_bodies.provenance.json", json.dumps({"payload_sha256": "x"}))
    monkeypatch.setattr(
        catalog_fallback.urllib.request,
        "urlopen",
        lambda *args, **kwargs: Response(archive.getvalue()),
    )
    with pytest.raises(catalog_fallback.CatalogArtifactError, match="must contain objects"):
        catalog_fallback.restore_latest_verified_catalog(
            output_path=tmp_path / "catalog.json",
            provenance_path=tmp_path / "provenance.json",
            repository="example/archive",
            workflow="rollout.yml",
            token="token",
        )

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(
            "discovered_bodies.json",
            json.dumps({"bodies": [], "provenance": {"payload_sha256": "expected"}}),
        )
        bundle.writestr(
            "discovered_bodies.provenance.json", json.dumps({"payload_sha256": "actual"})
        )
    monkeypatch.setattr(
        catalog_fallback.urllib.request,
        "urlopen",
        lambda *args, **kwargs: Response(archive.getvalue()),
    )
    with pytest.raises(catalog_fallback.CatalogArtifactError, match="checksum mismatch"):
        catalog_fallback.restore_latest_verified_catalog(
            output_path=tmp_path / "catalog.json",
            provenance_path=tmp_path / "provenance.json",
            repository="example/archive",
            workflow="rollout.yml",
            token="token",
        )


def test_restore_rejects_invalid_zip_and_skips_invalid_run(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        catalog_fallback,
        "_github_json",
        lambda url, token: {"workflow_runs": [{"id": "not-an-int"}]},
    )
    with pytest.raises(catalog_fallback.CatalogArtifactError, match="no successful"):
        catalog_fallback.restore_latest_verified_catalog(
            output_path=tmp_path / "catalog.json",
            provenance_path=tmp_path / "provenance.json",
            repository="example/archive",
            workflow="rollout.yml",
            token="token",
        )

    monkeypatch.setattr(
        catalog_fallback,
        "_github_json",
        lambda url, token: (
            {"workflow_runs": [{"id": 42}]}
            if url.endswith("/runs?status=success&per_page=20")
            else {
                "artifacts": [
                    {
                        "id": 1,
                        "name": "catalog-42",
                        "archive_download_url": "https://gh.test/catalog",
                    }
                ]
            }
        ),
    )
    monkeypatch.setattr(
        catalog_fallback.urllib.request,
        "urlopen",
        lambda *args, **kwargs: type(
            "Response",
            (),
            {
                "__enter__": lambda self: self,
                "__exit__": lambda self, *args: None,
                "read": lambda self: b"not-a-zip",
            },
        )(),
    )
    with pytest.raises(catalog_fallback.CatalogArtifactError, match="validation failed"):
        catalog_fallback.restore_latest_verified_catalog(
            output_path=tmp_path / "catalog.json",
            provenance_path=tmp_path / "provenance.json",
            repository="example/archive",
            workflow="rollout.yml",
            token="token",
        )
