"""Tests for unattended historical backfill dispatch planning."""

from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "plan_auto_backfill.py"
SPEC = importlib.util.spec_from_file_location("plan_auto_backfill", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load plan_auto_backfill.py")
plan_auto_backfill = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plan_auto_backfill)


def test_plan_dispatches_starts_from_lower_bound() -> None:
    plan = plan_auto_backfill.plan_dispatches(
        id_from=1,
        id_to=100,
        batch_span=25,
        max_batches=3,
    )

    assert plan["batches"] == [
        {"id_from": "1", "id_to": "25", "label": "1-25"},
        {"id_from": "26", "id_to": "50", "label": "26-50"},
        {"id_from": "51", "id_to": "75", "label": "51-75"},
    ]
    assert plan["next_id"] == 76
    assert plan["complete"] is False


def test_plan_dispatches_continues_from_state() -> None:
    plan = plan_auto_backfill.plan_dispatches(
        id_from=1,
        id_to=100,
        batch_span=25,
        max_batches=2,
        state={"next_id": 76},
    )

    assert plan["batches"] == [{"id_from": "76", "id_to": "100", "label": "76-100"}]
    assert plan["next_id"] == 101
    assert plan["complete"] is True


def test_plan_dispatches_clamps_stale_state_to_lower_bound() -> None:
    plan = plan_auto_backfill.plan_dispatches(
        id_from=50,
        id_to=60,
        batch_span=10,
        max_batches=1,
        state={"next_id": 1},
    )

    assert plan["batches"] == [{"id_from": "50", "id_to": "59", "label": "50-59"}]
    assert plan["next_id"] == 60
    assert plan["complete"] is False


def test_plan_dispatches_noops_after_completion() -> None:
    plan = plan_auto_backfill.plan_dispatches(
        id_from=1,
        id_to=10,
        batch_span=5,
        max_batches=2,
        state={"next_id": 11},
    )

    assert plan["batches"] == []
    assert plan["next_id"] == 11
    assert plan["complete"] is True
