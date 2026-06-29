"""Tests for historical backfill chunk planning."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "plan_backfill_chunks.py"
SPEC = importlib.util.spec_from_file_location("plan_backfill_chunks", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load plan_backfill_chunks.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
plan_chunks = MODULE.plan_chunks


def test_plan_chunks_uses_inclusive_ranges() -> None:
    matrix = plan_chunks(id_from=1, id_to=250, chunk_size=100)

    assert matrix == {
        "include": [
            {"id_from": "1", "id_to": "100", "label": "1-100"},
            {"id_from": "101", "id_to": "200", "label": "101-200"},
            {"id_from": "201", "id_to": "250", "label": "201-250"},
        ],
    }


def test_plan_chunks_can_cap_chunk_count() -> None:
    matrix = plan_chunks(id_from=1, id_to=1000, chunk_size=100, max_chunks=2)

    assert matrix["include"][-1] == {"id_from": "101", "id_to": "200", "label": "101-200"}


def test_plan_chunks_rejects_invalid_ranges() -> None:
    with pytest.raises(ValueError, match="id_from must be <= id_to"):
        plan_chunks(id_from=10, id_to=1, chunk_size=10)
