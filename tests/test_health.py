"""Tests for archive health parity."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from fyi_archive.cli import app
from fyi_archive.health import live_mirror_counts, manifest_count, parity_report


def test_manifest_count_reads_meta_record_count(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"meta": {"record_count": 3, "generated_at": "2026-01-01T00:00:00Z"}}),
        encoding="utf-8",
    )

    assert manifest_count(manifest) == (3, "2026-01-01T00:00:00Z")


def test_manifest_count_missing_file(tmp_path: Path) -> None:
    assert manifest_count(tmp_path / "nope.json") == (0, None)


def test_parity_report_flags_drift() -> None:
    report = parity_report(
        manifest_records=10,
        mirror_records={"huggingface": 10, "zenodo": 1},
        tolerance=2,
    )

    assert report["healthy"] is False
    assert report["mirrors"]["zenodo"]["within_tolerance"] is False


def test_live_mirror_counts_prefers_positive_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("HF_RECORD_COUNT", "12")
    monkeypatch.setenv("ZENODO_RECORD_COUNT", "12")
    monkeypatch.setenv("OSF_RECORD_COUNT", "12")
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("HF_REPO_ID", raising=False)

    counts = live_mirror_counts()

    assert counts["huggingface"]["count"] == 12
    assert counts["huggingface"]["source"] == "env"
    assert counts["zenodo"]["source"] == "env"
    assert counts["osf"]["source"] == "env"


def test_live_mirror_counts_queries_huggingface(monkeypatch) -> None:
    monkeypatch.delenv("HF_RECORD_COUNT", raising=False)
    monkeypatch.setenv("HF_TOKEN", "hf-token")
    monkeypatch.setenv("HF_REPO_ID", "owner/dataset")
    monkeypatch.delenv("ZENODO_RECORD_COUNT", raising=False)
    monkeypatch.delenv("ZENODO_TOKEN", raising=False)
    monkeypatch.delenv("OSF_RECORD_COUNT", raising=False)
    monkeypatch.delenv("OSF_TOKEN", raising=False)

    monkeypatch.setattr(
        "fyi_archive.backfill_verification.remote_huggingface_record_count",
        lambda **kwargs: {
            "record_count": 42,
            "manifest_sha256": "abc",
            "repo_id": kwargs["repo_id"],
        },
    )

    counts = live_mirror_counts()

    assert counts["huggingface"]["count"] == 42
    assert counts["huggingface"]["source"] == "huggingface"
    assert counts["zenodo"]["source"] in {"unavailable", "env"}
    assert counts["osf"]["source"] in {"unavailable", "env"}


def test_live_mirror_counts_huggingface_error(monkeypatch) -> None:
    monkeypatch.delenv("HF_RECORD_COUNT", raising=False)
    monkeypatch.setenv("HF_TOKEN", "hf-token")
    monkeypatch.setenv("HF_REPO_ID", "owner/dataset")

    def _boom(**kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(
        "fyi_archive.backfill_verification.remote_huggingface_record_count",
        _boom,
    )
    monkeypatch.setenv("ZENODO_RECORD_COUNT", "1")
    monkeypatch.setenv("OSF_RECORD_COUNT", "1")

    counts = live_mirror_counts()
    assert counts["huggingface"]["source"] == "error"
    assert "network down" in counts["huggingface"]["error"]


def test_live_mirror_counts_queries_zenodo(monkeypatch) -> None:
    monkeypatch.delenv("ZENODO_RECORD_COUNT", raising=False)
    monkeypatch.setenv("ZENODO_TOKEN", "z-token")
    monkeypatch.setenv("ZENODO_DEPOSITION_ID", "99")
    monkeypatch.setenv("HF_RECORD_COUNT", "1")
    monkeypatch.setenv("OSF_RECORD_COUNT", "1")
    monkeypatch.setattr(
        "fyi_archive.backfill_verification.remote_zenodo_record_count",
        lambda **kwargs: {"record_count": 7, "doi": "10.1/x", "deposition_id": 99},
    )

    counts = live_mirror_counts()
    assert counts["zenodo"]["count"] == 7
    assert counts["zenodo"]["source"] == "zenodo"


def test_live_mirror_counts_queries_osf(monkeypatch) -> None:
    monkeypatch.delenv("OSF_RECORD_COUNT", raising=False)
    monkeypatch.setenv("OSF_TOKEN", "osf-token")
    monkeypatch.setenv("OSF_PARENT_ID", "abc12")
    monkeypatch.setenv("HF_RECORD_COUNT", "1")
    monkeypatch.setenv("ZENODO_RECORD_COUNT", "1")

    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"meta": {"record_count": 5}}

    monkeypatch.setattr(
        "fyi_archive.publish.osf_publish.list_files",
        lambda **kwargs: [
            SimpleNamespace(name="latest_manifest.json", url="https://osf.example/m")
        ],
    )
    monkeypatch.setattr("httpx.get", lambda *args, **kwargs: _Resp())

    counts = live_mirror_counts()
    assert counts["osf"]["count"] == 5
    assert counts["osf"]["source"] == "osf"


def test_live_mirror_counts_osf_missing_manifest(monkeypatch) -> None:
    monkeypatch.delenv("OSF_RECORD_COUNT", raising=False)
    monkeypatch.setenv("OSF_TOKEN", "osf-token")
    monkeypatch.setenv("OSF_NODE_ID", "node1")
    monkeypatch.setenv("HF_RECORD_COUNT", "1")
    monkeypatch.setenv("ZENODO_RECORD_COUNT", "1")
    monkeypatch.setattr(
        "fyi_archive.publish.osf_publish.list_files",
        lambda **kwargs: [SimpleNamespace(name="other.txt", url="https://osf.example/o")],
    )

    counts = live_mirror_counts()
    assert counts["osf"]["count"] == 0
    assert counts["osf"]["source"] == "unavailable"
    assert "not found" in counts["osf"]["note"]


def test_doctor_exits_nonzero_on_drift(tmp_path: Path, monkeypatch) -> None:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    (manifest_dir / "latest_manifest.json").write_text(
        json.dumps({"meta": {"record_count": 10, "generated_at": "2026-01-01T00:00:00Z"}}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HF_RECORD_COUNT", "10")
    monkeypatch.setenv("ZENODO_RECORD_COUNT", "0")
    monkeypatch.setenv("OSF_RECORD_COUNT", "10")
    monkeypatch.delenv("ZENODO_TOKEN", raising=False)
    monkeypatch.delenv("ZENODO_DEPOSITION_ID", raising=False)

    result = CliRunner().invoke(app, ["doctor", "check", "--tolerance", "1"])

    assert result.exit_code == 1
    assert '"status": "drift"' in result.stdout


def test_doctor_healthy_with_matching_env_counts(tmp_path: Path, monkeypatch) -> None:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    (manifest_dir / "latest_manifest.json").write_text(
        json.dumps({"meta": {"record_count": 10, "generated_at": "2026-01-01T00:00:00Z"}}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HF_RECORD_COUNT", "10")
    monkeypatch.setenv("ZENODO_RECORD_COUNT", "10")
    monkeypatch.setenv("OSF_RECORD_COUNT", "10")

    result = CliRunner().invoke(app, ["doctor", "check", "--tolerance", "1"])

    assert result.exit_code == 0, result.output
    assert '"status": "healthy"' in result.stdout
    health = json.loads((tmp_path / "conductor/archive_health.json").read_text(encoding="utf-8"))
    assert health["coverage"]["records"] == 10


def test_doctor_falls_back_to_huggingface_manifest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("HF_RECORD_COUNT", raising=False)
    monkeypatch.setenv("HF_TOKEN", "hf-token")
    monkeypatch.setenv("HF_REPO_ID", "owner/dataset")
    monkeypatch.setenv("ZENODO_RECORD_COUNT", "42")
    monkeypatch.setenv("OSF_RECORD_COUNT", "42")
    monkeypatch.setattr(
        "fyi_archive.backfill_verification.remote_huggingface_record_count",
        lambda **kwargs: {"record_count": 42, "manifest_sha256": "x", "repo_id": "owner/dataset"},
    )

    result = CliRunner().invoke(app, ["doctor", "check", "--tolerance", "1"])

    assert result.exit_code == 0, result.output
    assert '"source": "huggingface"' in result.stdout
