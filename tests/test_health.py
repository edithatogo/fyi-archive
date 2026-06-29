"""Tests for archive health parity."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from fyi_archive.cli import app
from fyi_archive.health import manifest_count, parity_report


def test_manifest_count_reads_meta_record_count(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"meta": {"record_count": 3, "generated_at": "2026-01-01T00:00:00Z"}}),
        encoding="utf-8",
    )

    assert manifest_count(manifest) == (3, "2026-01-01T00:00:00Z")


def test_parity_report_flags_drift() -> None:
    report = parity_report(
        manifest_records=10,
        mirror_records={"huggingface": 10, "zenodo": 1},
        tolerance=2,
    )

    assert report["healthy"] is False
    assert report["mirrors"]["zenodo"]["within_tolerance"] is False


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

    result = CliRunner().invoke(app, ["doctor", "check", "--tolerance", "1"])

    assert result.exit_code == 1
    assert '"status": "drift"' in result.stdout
