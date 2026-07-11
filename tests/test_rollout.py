"""Tests for ordered AU rollout planning and controller state."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fyi_archive.rollout import initial_rollout_state, load_rollout_config, write_rollout_state


def test_rollout_config_is_ordered_and_shared_rate_limited() -> None:
    config = load_rollout_config()
    assert config["instance_id"] == "au-rtk"
    assert config["shared_rate_limit_name"] == "archive-discovery-au-rtk"
    assert config["jurisdictions"][0] == "NSW"
    assert len(config["jurisdictions"]) == 10


def test_rollout_config_rejects_duplicate_or_unknown_jurisdiction(tmp_path: Path) -> None:
    config = load_rollout_config()
    config["jurisdictions"] = ["NSW", "NSW"]
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        load_rollout_config(path)

    config["jurisdictions"] = ["NSW", "UNKNOWN"]
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown"):
        load_rollout_config(path)


def test_rollout_state_is_written_atomically(tmp_path: Path) -> None:
    state = initial_rollout_state(load_rollout_config())
    path = tmp_path / "state.json"
    write_rollout_state(path, state)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["jurisdictions"]["NSW"]["status"] == "pending"
    assert not path.with_suffix(".json.tmp").exists()


def test_rollout_workflow_retains_the_catalog_it_produces() -> None:
    workflow = Path(".github/workflows/au_jurisdiction_rollout.yml").read_text(encoding="utf-8")
    assert "data/au-rtk/rollout/discovered_bodies.json" in workflow
    assert "data/_state/discovered_bodies.json" not in workflow
    assert "actions: read" in workflow
