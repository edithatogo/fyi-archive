"""Tests for the fyi-cli body-discovery delegation boundary."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer import BadParameter

import fyi_archive.commands.discover as discover_command
from fyi_archive.body_discovery import discover_bodies_with_fallback, discover_bodies_with_fyi_cli


def test_discover_bodies_delegates_to_fyi_cli(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "bodies.json"
    limiter = tmp_path / "state" / "fyi-cli.db"

    def fake_run(command, *, check, capture_output, text):
        assert Path(command[0]).name in {"python", "python3", "python.exe"}
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


def test_fallback_preserves_last_good_until_verified_restore(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "bodies.json"
    provenance = tmp_path / "bodies.provenance.json"
    limiter = tmp_path / "state" / "fyi-cli.db"
    output.write_text(json.dumps({"bodies": [{"name": "old"}]}), encoding="utf-8")

    def fail_live(**kwargs):
        kwargs["output_path"].write_text('{"bodies": [{"name": "bad"}]}', encoding="utf-8")
        raise RuntimeError("HTTP 403")

    def restore(**kwargs):
        kwargs["output_path"].write_text(
            json.dumps(
                {
                    "bodies": [{"name": "verified"}],
                    "provenance": {"payload_sha256": "abc"},
                }
            ),
            encoding="utf-8",
        )
        kwargs["provenance_path"].write_text(
            json.dumps({"mode": "fallback", "failure_class": "RuntimeError"}), encoding="utf-8"
        )

    monkeypatch.setattr("fyi_archive.body_discovery.discover_bodies_with_fyi_cli", fail_live)
    monkeypatch.setattr("fyi_archive.body_discovery.restore_latest_verified_catalog", restore)
    payload = discover_bodies_with_fallback(
        base_url="https://capture.example",
        output_path=output,
        provenance_path=provenance,
        shared_rate_limit_db=limiter,
        repository="example/archive",
        workflow="rollout.yml",
        catalog_url="https://catalog.example/au.csv",
    )

    assert payload["bodies"] == [{"name": "verified"}]
    assert json.loads(output.read_text(encoding="utf-8"))["bodies"] == [{"name": "verified"}]
    assert json.loads(provenance.read_text(encoding="utf-8"))["mode"] == "fallback"


def test_live_success_writes_verified_provenance(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "bodies.json"
    provenance = tmp_path / "bodies.provenance.json"

    def live(**kwargs):
        kwargs["output_path"].write_text(
            json.dumps(
                {
                    "bodies": [{"name": "live"}],
                    "provenance": {"payload_sha256": "abc"},
                }
            ),
            encoding="utf-8",
        )
        return {"bodies": [{"name": "live"}], "provenance": {"payload_sha256": "abc"}}

    monkeypatch.setattr("fyi_archive.body_discovery.discover_bodies_with_fyi_cli", live)
    monkeypatch.setattr(
        "fyi_archive.body_discovery.restore_latest_verified_catalog",
        lambda **kwargs: pytest.fail("fallback should not run"),
    )
    payload = discover_bodies_with_fallback(
        base_url="https://capture.example",
        output_path=output,
        provenance_path=provenance,
        shared_rate_limit_db=tmp_path / "limiter.db",
        repository="example/archive",
        workflow="rollout.yml",
    )

    assert payload["bodies"] == [{"name": "live"}]
    assert json.loads(output.read_text(encoding="utf-8"))["bodies"] == [{"name": "live"}]
    assert json.loads(provenance.read_text(encoding="utf-8"))["mode"] == "live"


def test_discover_command_writes_provenance_for_live_payload(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "bodies.json"
    provenance = tmp_path / "provenance.json"

    class _Instance:
        id = "test-instance"

        @staticmethod
        def capture_base_url() -> str:
            return "https://capture.example"

    monkeypatch.setattr(discover_command, "resolve_instance", lambda **_: _Instance())
    monkeypatch.setattr(
        discover_command,
        "discover_bodies_with_fyi_cli",
        lambda **_: {"bodies": [{"name": "live"}], "provenance": {"mode": "default"}},
    )
    written: dict[str, object] = {}
    monkeypatch.setattr(
        discover_command,
        "write_catalog_provenance",
        lambda path, payload: written.update(path=path, payload=payload),
    )

    discover_command.bodies(output=output, provenance=provenance)

    assert written == {"path": provenance, "payload": {"mode": "default"}}


def test_discover_command_rejects_fallback_without_repository(tmp_path: Path) -> None:
    with pytest.raises(BadParameter, match="--repository is required"):
        discover_command.bodies(output=tmp_path / "bodies.json", fallback=True)
