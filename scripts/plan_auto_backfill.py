#!/usr/bin/env python3
"""Plan unattended FYI historical backfill worker dispatches."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backfill_state import has_pending_batches, state_next_id


def plan_dispatches(
    *,
    id_from: int,
    id_to: int,
    batch_span: int,
    max_batches: int,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the next bounded set of backfill worker dispatches."""
    if id_from < 1 or id_to < 1:
        msg = "id_from and id_to must be positive"
        raise ValueError(msg)
    if id_from > id_to:
        msg = "id_from must be <= id_to"
        raise ValueError(msg)
    if batch_span < 1:
        msg = "batch_span must be positive"
        raise ValueError(msg)
    if max_batches < 1:
        msg = "max_batches must be positive"
        raise ValueError(msg)

    current = max(state_next_id(state, id_from), id_from)
    if has_pending_batches(state):
        return {
            "batches": [],
            "blocked_by_pending": True,
            "complete": False,
            "next_id": current,
            "planned_count": 0,
        }
    batches: list[dict[str, str]] = []
    for _ in range(max_batches):
        if current > id_to:
            break
        batch_end = min(current + batch_span - 1, id_to)
        batches.append(
            {
                "id_from": str(current),
                "id_to": str(batch_end),
                "label": f"{current}-{batch_end}",
            }
        )
        current = batch_end + 1

    return {
        "batches": batches,
        "blocked_by_pending": False,
        "complete": current > id_to,
        "next_id": min(current, id_to + 1),
        "planned_count": len(batches),
    }


def load_state(path: Path | None) -> dict[str, Any] | None:
    """Load optional controller state JSON."""
    if path is None or not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    data = json.loads(text)
    if not isinstance(data, dict):
        msg = "state JSON must be an object"
        raise ValueError(msg)
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id-from", type=int, required=True)
    parser.add_argument("--id-to", type=int, required=True)
    parser.add_argument("--batch-span", type=int, required=True)
    parser.add_argument("--max-batches", type=int, required=True)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    plan = plan_dispatches(
        id_from=args.id_from,
        id_to=args.id_to,
        batch_span=args.batch_span,
        max_batches=args.max_batches,
        state=load_state(args.state),
    )
    payload = json.dumps(plan, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(json.dumps(plan, sort_keys=True))


if __name__ == "__main__":
    main()
