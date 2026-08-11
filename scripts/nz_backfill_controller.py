#!/usr/bin/env python3
"""Read and update durable NZ real-backfill controller state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fyi_archive.backfill_state_codec import decode_state, state_body_from_state
from fyi_archive.nz_backfill_state import complete_range, next_unclaimed_offset, reserve_range


def main() -> None:
    """Apply one fail-closed controller transition."""
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("reserve", "complete", "next"))
    parser.add_argument("--body", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--start-offset", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    state = decode_state(args.body.read_text(encoding="utf-8"))
    if args.action == "next":
        print(next_unclaimed_offset(state))
        return
    if args.output is None or args.run_id is None:
        parser.error("--output and --run-id are required for state updates")
    if args.action == "reserve":
        if args.start_offset is None or args.batch_size is None:
            parser.error("--start-offset and --batch-size are required to reserve")
        updated = reserve_range(
            state,
            start_offset=args.start_offset,
            batch_size=args.batch_size,
            run_id=args.run_id,
        )
    else:
        if args.receipt is None:
            parser.error("--receipt is required to complete")
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        updated = complete_range(state, run_id=args.run_id, receipt=receipt)
    args.output.write_text(state_body_from_state(updated), encoding="utf-8")


if __name__ == "__main__":
    main()
