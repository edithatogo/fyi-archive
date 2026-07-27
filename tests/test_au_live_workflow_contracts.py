"""Contracts for intentional AU live-operation dispatch."""

from pathlib import Path


def test_au_live_workflows_require_machine_readiness_and_environment() -> None:
    for name in ("au_nsw_historical_seed.yml", "au_jurisdiction_rollout.yml"):
        workflow = Path(".github/workflows", name).read_text(encoding="utf-8")
        assert "environment: au-live-capture" in workflow
        assert "AUTONOMOUS_AU_CAPTURE_ENABLED" in workflow
        assert "confirm_live:" not in workflow
        assert "after recording readiness evidence" in workflow
