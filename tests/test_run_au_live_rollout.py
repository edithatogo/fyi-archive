from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("run_au_live_rollout", "scripts/run_au_live_rollout.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
LIVE_CAPTURE_CONFIRMATION = MODULE.LIVE_CAPTURE_CONFIRMATION
run_live_rollout = MODULE.run_live_rollout


def test_live_rollout_requires_explicit_confirmation(tmp_path: Path) -> None:
    args = Namespace(confirm_live_capture="", output_dir=tmp_path)

    with pytest.raises(ValueError, match="explicit live-capture confirmation"):
        run_live_rollout(args)


def test_live_rollout_confirmation_constant_is_narrow() -> None:
    assert LIVE_CAPTURE_CONFIRMATION == "I_CONFIRM_BOUNDED_READ_ONLY_CAPTURE"


def test_empirical_pilot_config_is_limited_to_commonwealth_and_nsw() -> None:
    config_path = Path("configs/au/jurisdiction_rollout_empirical_pilot.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["instance_id"] == "au-rtk"
    assert config["jurisdictions"] == ["NSW", "FEDERAL"]
