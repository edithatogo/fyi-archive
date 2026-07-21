from __future__ import annotations

from argparse import Namespace
import importlib.util
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
