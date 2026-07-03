"""Tests for security-report redaction helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


def load_script(name: str):
    script_path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_validate_secrets_reports_labels_without_raw_env_names(monkeypatch, capsys) -> None:
    script = load_script("validate_secrets")
    monkeypatch.setenv("HF_TOKEN", "present")
    monkeypatch.setenv("HF_REPO_ID", "present")
    monkeypatch.setenv("ZENODO_TOKEN", "present")
    monkeypatch.setenv("OSF_TOKEN", "present")
    monkeypatch.setenv("OSF_PARENT_ID", "present")
    monkeypatch.delenv("ZENODO_SANDBOX_TOKEN", raising=False)

    with pytest.raises(SystemExit) as excinfo:
        script.main()

    assert excinfo.value.code == 0
    stdout = capsys.readouterr().out
    assert "HF_TOKEN" not in stdout
    assert "OSF_PARENT_ID" not in stdout
    assert "missing_required_services" in stdout


def test_audit_credentials_redacts_secret_names_and_values(tmp_path: Path, monkeypatch) -> None:
    script = load_script("audit_credentials")
    env_file = tmp_path / ".env"
    env_file.write_text("HF_TOKEN=super-secret-value\n", encoding="utf-8")

    monkeypatch.setattr(
        script,
        "gh_json",
        lambda args: (
            [{"name": "HF_TOKEN", "updatedAt": "2026-07-03T00:00:00Z"}]
            if "secret" in args
            else [{"name": "HF_REPO_ID", "updatedAt": "2026-07-03T00:00:00Z"}]
        ),
    )

    inventory = script.build_inventory("edithatogo/fyi-archive", [tmp_path])
    serialized = json.dumps(inventory)

    assert inventory["github_actions"]["secret_count"] == 1
    assert inventory["github_actions"]["variable_count"] == 1
    assert inventory["environment"]["Hugging Face token"]["value_status"] == "missing"
    assert inventory["local_file_mentions"][0]["service"] == "Hugging Face token"
    assert inventory["local_file_mentions"][0]["value_status"] == "present"
    assert "HF_TOKEN" not in serialized
    assert "HF_REPO_ID" not in serialized
    assert "super-secret-value" not in serialized
