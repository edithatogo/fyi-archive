from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_quality_profile_declares_locked_canary_and_type_lanes() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dev = project["project"]["optional-dependencies"]["dev"]
    assert any(item.startswith("basedpyright") for item in dev)
    assert (ROOT / "uv.lock").is_file()
    assert (ROOT / "docs/quality-profile.md").is_file()
    assert (ROOT / ".github/workflows/python-canary.yml").is_file()


def test_quality_profile_keeps_llm_orchestration_out_of_runtime_dependencies() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dependencies = project["project"]["dependencies"]
    assert not any(
        item.lower().startswith(("pydantic-ai", "dspy", "litellm")) for item in dependencies
    )
