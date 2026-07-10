"""Tests for the fyi-cli body-discovery delegation boundary."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from fyi_archive.body_discovery import discover_bodies_with_fyi_cli


def test_discover_bodies_delegates_to_fyi_cli(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "bodies.json"
    limiter = tmp_path / "state" / "fyi-cli.db"

    def fake_run(command, *, check, capture_output, text):
        assert command[0].endswith("python.exe") or command[0].endswith("python")
        assert command[1:4] == ["-m", "fyi_system.cli", "discover-bodies"]
        assert "--base-url" in command
        assert "--db" in command
        assert str(limiter) in command
        output.write_text(
            json.dumps({"base_url": "https://example.test", "count": 1, "bodies": []})
        )

    monkeypatch.setattr("fyi_archive.body_discovery.subprocess.run", fake_run)
    payload = discover_bodies_with_fyi_cli(
        base_url="https://example.test",
        output_path=output,
        shared_rate_limit_db=limiter,
    )

    assert payload["count"] == 1
    assert output.exists()


def test_discover_bodies_retries_and_reports_cli_stderr(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "bodies.json"
    limiter = tmp_path / "state" / "fyi-cli.db"
    attempts = 0

    def fake_run(command, *, check, capture_output, text):
        nonlocal attempts
        attempts += 1
        raise subprocess.CalledProcessError(1, command, output="", stderr="upstream read timeout")

    monkeypatch.setattr("fyi_archive.body_discovery.subprocess.run", fake_run)
    monkeypatch.setattr("fyi_archive.body_discovery.time.sleep", lambda _: None)

    with pytest.raises(RuntimeError, match="after 3 attempts: upstream read timeout"):
        discover_bodies_with_fyi_cli(
            base_url="https://example.test",
            output_path=output,
            shared_rate_limit_db=limiter,
        )
    assert attempts == 3
