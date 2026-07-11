"""Contracts for intentional AU live-operation dispatch."""

from pathlib import Path


def test_au_live_workflows_require_explicit_confirmation_and_environment() -> None:
    for name in ("au_nsw_historical_seed.yml", "au_jurisdiction_rollout.yml"):
        workflow = Path(".github/workflows", name).read_text(encoding="utf-8")
        assert "environment: au-live-capture" in workflow
        assert "RUN_LIVE_AU_CAPTURE" in workflow
        assert "Live AU capture requires confirm_live=RUN_LIVE_AU_CAPTURE" in workflow
