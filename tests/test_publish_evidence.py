"""Tests for versioned publication verification evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import respx
from httpx import Response
from typer.testing import CliRunner

from fyi_archive import __version__
from fyi_archive.cli import app
from fyi_archive.publish.evidence import (
    archive_publication_version,
    repo_relative_path,
    verify_huggingface_dataset,
    write_versioned_verification_bundle,
)
from fyi_archive.publish.verification import MirrorVerification

runner = CliRunner()


def test_archive_publication_version_is_monthly() -> None:
    generated_at = datetime(2026, 6, 30, tzinfo=UTC)

    version = archive_publication_version(generated_at=generated_at, package_version="1.2.3")

    assert version == "1.2.3+archive.2026.06"


def test_write_versioned_verification_bundle(tmp_path: Path) -> None:
    manifest = tmp_path / "manifests/latest_manifest.json"
    manifest.parent.mkdir()
    manifest.write_text('{"meta": {"record_count": 3}, "requests": []}\n', encoding="utf-8")
    report = MirrorVerification(mirror="huggingface", verified=True, record_count=3)

    bundle = write_versioned_verification_bundle(
        reports=[report],
        manifest_path=manifest,
        output_dir=tmp_path / "versions",
        generated_at=datetime(2026, 6, 30, tzinfo=UTC),
    )

    assert bundle["archive_publication_version"] == f"{__version__}+archive.2026.06"
    assert (tmp_path / "versions/2026-06/mirror_verification.json").exists()
    assert (tmp_path / "versions/latest_mirror_verification.json").exists()


def test_verify_huggingface_dataset_compares_snapshot_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest = tmp_path / "manifests/latest_manifest.json"
    manifest.parent.mkdir()
    manifest.write_text('{"meta": {"record_count": 1}, "requests": []}\n', encoding="utf-8")
    snapshot = tmp_path / "snapshot"
    remote_manifest = snapshot / "manifests/latest_manifest.json"
    remote_manifest.parent.mkdir(parents=True)
    remote_manifest.write_text(manifest.read_text(encoding="utf-8"), encoding="utf-8")

    def fake_snapshot_download(**kwargs: object) -> str:
        assert kwargs["allow_patterns"] == ["manifests/latest_manifest.json"]
        return str(snapshot)

    monkeypatch.setattr("fyi_archive.publish.evidence.snapshot_download", fake_snapshot_download)

    report = verify_huggingface_dataset(
        repo_id="owner/dataset",
        token="token",
        local_artifacts=[manifest],
        manifest_path=manifest,
        repo_root=tmp_path,
    )

    assert report.verified is True
    assert report.artifacts[0].checksum_matches is True


def test_repo_relative_path_handles_relative_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    manifest = Path("mirror-root/manifests/latest_manifest.json")
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")

    relative = repo_relative_path(manifest.resolve(), Path("mirror-root").resolve())

    assert relative.as_posix() == "manifests/latest_manifest.json"


@respx.mock
def test_publish_verify_cli_writes_zenodo_versioned_evidence(tmp_path: Path) -> None:
    manifest = tmp_path / "manifests/latest_manifest.json"
    manifest.parent.mkdir()
    manifest.write_text('{"meta": {"record_count": 1}, "requests": []}\n', encoding="utf-8")
    local_sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
    respx.get("https://zenodo.example/api/deposit/depositions/42").mock(
        return_value=Response(
            200,
            json={
                "doi": "10.5281/zenodo.42",
                "files": [
                    {
                        "filename": "latest_manifest.json",
                        "filesize": manifest.stat().st_size,
                        "checksum": f"sha256:{local_sha}",
                    },
                ],
            },
        ),
    )

    result = runner.invoke(
        app,
        [
            "publish",
            "verify",
            "--root",
            str(tmp_path),
            "--artifact",
            "manifests/latest_manifest.json",
            "--zenodo-deposition-id",
            "42",
            "--zenodo-token",
            "token",
            "--zenodo-api-url",
            "https://zenodo.example/api",
        ],
    )

    assert result.exit_code == 0, result.output
    latest = tmp_path / "versions/latest_mirror_verification.json"
    assert latest.exists()
    payload = json.loads(latest.read_text(encoding="utf-8"))
    assert payload["mirrors"][0]["mirror"] == "zenodo"
    assert payload["verified"] is True
