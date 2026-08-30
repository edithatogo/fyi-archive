"""Machine-readable sync summaries must survive noisy child processes."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fyi_archive.commands.sync import app
from fyi_archive.sync import run_fyi_cli_diff
from fyi_archive.sync_summary import validate_summary, write_summary


def summary() -> dict[str, object]:
    return {
        "generated_at": "2026-08-30T00:00:00+00:00",
        "record_count": 3,
        "manifest_sha256": "a" * 64,
        "verified": True,
        "instance_id": "nz-fyi",
    }


def test_cli_writes_dedicated_summary(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("fyi_archive.commands.sync.run_sync", lambda **_: summary())
    target = tmp_path / "summary.json"
    result = CliRunner().invoke(app, ["--summary-path", str(target)])
    assert result.exit_code == 0, result.output
    assert json.loads(target.read_text()) == summary()
    assert json.loads(result.stdout) == summary()


def test_failed_sync_removes_stale_summary(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "summary.json"
    target.write_text(json.dumps(summary()))

    def fail(**_):
        raise RuntimeError("verification failed")

    monkeypatch.setattr("fyi_archive.commands.sync.run_sync", fail)
    result = CliRunner().invoke(app, ["--summary-path", str(target)])
    assert result.exit_code != 0
    assert not target.exists()


def test_python_diagnostics_are_separate_from_json_stdout(tmp_path: Path, monkeypatch) -> None:
    def noisy(**_):
        print("capture diagnostic")
        return summary()

    monkeypatch.setattr("fyi_archive.commands.sync.run_sync", noisy)
    result = CliRunner().invoke(app, ["--summary-path", str(tmp_path / "summary.json")])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == summary()
    assert "capture diagnostic" in result.stderr


def test_summary_cannot_overwrite_controller_state(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    state.write_text("existing state")
    result = CliRunner().invoke(app, ["--summary-path", str(state), "--state-path", str(state)])
    assert result.exit_code != 0
    assert state.read_text() == "existing state"


def test_child_diagnostics_never_use_summary_stdout(tmp_path: Path, monkeypatch) -> None:
    def child(command, **kwargs):
        assert kwargs["stdout"] is sys.stderr
        assert kwargs["check"] is True

    monkeypatch.setattr("fyi_archive.sync.subprocess.run", child)
    run_fyi_cli_diff(
        since=None,
        derived_dir=tmp_path,
        previous_manifest=tmp_path / "old.json",
        output_path=tmp_path / "changes.json",
    )


@pytest.mark.parametrize(
    "change",
    [
        {"instance_id": "au-rtk"},
        {"record_count": -1},
        {"verified": "true"},
        {"manifest_sha256": "short"},
    ],
)
def test_card_script_rejects_wrong_identity_and_invalid_summary(tmp_path: Path, change) -> None:
    source = tmp_path / "summary.json"
    source.write_text(json.dumps({**summary(), **change}))
    card = tmp_path / "card.md"
    card.write_text("# Card\n")
    output = tmp_path / "output.md"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/render_dataset_card.py",
            "--summary",
            str(source),
            "--card",
            str(card),
            "--output",
            str(output),
            "--instance",
            "nz-fyi",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert not output.exists()


@pytest.mark.parametrize(
    "change",
    [
        {"instance_id": "au-rtk"},
        {"record_count": -1},
        {"record_count": True},
        {"manifest_sha256": "bad"},
        {"verified": "true"},
        {"generated_at": None},
        {"generated_at": "2026-08-30T00:00:00"},
    ],
)
def test_summary_validator_rejects_invalid_metadata(change) -> None:
    with pytest.raises(ValueError, match="sync summary"):
        validate_summary({**summary(), **change}, instance_id="nz-fyi")


@pytest.mark.parametrize("verified", [True, False, None])
def test_summary_validator_preserves_verification_states(verified) -> None:
    validate_summary({**summary(), "verified": verified}, instance_id="nz-fyi")


def test_atomic_summary_failure_preserves_previous_artifact(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "summary.json"
    target.write_text("previous artifact")

    def interrupted(self, destination):
        raise OSError("interrupted replace")

    monkeypatch.setattr(Path, "replace", interrupted)
    with pytest.raises(OSError, match="interrupted replace"):
        write_summary(target, summary(), instance_id="nz-fyi")
    assert target.read_text() == "previous artifact"
    assert list(tmp_path.iterdir()) == [target]
