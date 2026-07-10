"""Deterministic AU jurisdiction rollout planning and controller state."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fyi_archive.jurisdictions import load_jurisdiction_rules

DEFAULT_ROLLOUT_PATH = Path(__file__).parents[2] / "configs" / "au" / "jurisdiction_rollout.json"


def load_rollout_config(path: Path = DEFAULT_ROLLOUT_PATH) -> dict[str, Any]:
    """Load and validate the ordered AU rollout configuration."""
    config = json.loads(path.read_text(encoding="utf-8"))
    jurisdictions = config.get("jurisdictions")
    rules = load_jurisdiction_rules()
    known = set(rules["jurisdictions"])
    if config.get("instance_id") != "au-rtk":
        raise ValueError("AU rollout must target the au-rtk instance")
    if (
        not isinstance(config.get("shared_rate_limit_name"), str)
        or not config["shared_rate_limit_name"].strip()
    ):
        raise ValueError("AU rollout requires a shared rate-limit name")
    if not isinstance(jurisdictions, list) or not jurisdictions:
        raise ValueError("AU rollout jurisdictions must be a non-empty list")
    normalized = [str(item).strip().upper() for item in jurisdictions]
    if len(normalized) != len(set(normalized)):
        raise ValueError("AU rollout jurisdictions must be unique")
    unknown = sorted(set(normalized) - known)
    if unknown:
        raise ValueError(f"AU rollout contains unknown jurisdictions: {', '.join(unknown)}")
    if normalized[0] != "NSW":
        raise ValueError("AU rollout must begin with the completed NSW seed")
    return {**config, "jurisdictions": normalized}


def initial_rollout_state(config: dict[str, Any]) -> dict[str, Any]:
    """Create resumable controller state without claiming any work completed."""
    now = datetime.now(UTC).isoformat()
    return {
        "instance_id": config["instance_id"],
        "shared_rate_limit_name": config["shared_rate_limit_name"],
        "updated_at": now,
        "jurisdictions": {
            jurisdiction: {"status": "pending", "updated_at": now}
            for jurisdiction in config["jurisdictions"]
        },
        "national_manifest": {"status": "pending"},
    }


def write_rollout_state(path: Path, state: dict[str, Any]) -> None:
    """Write controller state atomically enough for workflow artifact recovery."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
