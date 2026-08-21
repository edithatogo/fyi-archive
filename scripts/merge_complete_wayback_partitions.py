"""Merge a declared set of complete, hash-valid Wayback time partitions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fyi_archive.wayback_partitions import TimePartition, merge_complete_partition_exports


def _plan_path(root: Path, value: object) -> Path:
    relative = Path(str(value))
    if relative.is_absolute():
        raise ValueError("partition file paths must be relative")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("partition file path escapes the declared root") from error
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    if plan.get("schema") != "fyi-archive.wayback-partition-plan.v1":
        raise ValueError("unsupported Wayback partition plan")
    raw_partitions = plan.get("partitions")
    if not isinstance(raw_partitions, list):
        raise ValueError("partition plan requires a partitions array")
    partitions: list[tuple[TimePartition, Path, Path]] = []
    for raw in raw_partitions:
        if not isinstance(raw, dict):
            raise ValueError("partition entries must be objects")
        partition = TimePartition(
            id=str(raw["id"]),
            from_timestamp=str(raw["from_timestamp"]),
            to_timestamp=(
                str(raw["to_timestamp"]) if raw.get("to_timestamp") is not None else None
            ),
        )
        partitions.append((
            partition,
            _plan_path(args.root, raw["output"]),
            _plan_path(args.root, raw["evidence"]),
        ))
    merge_complete_partition_exports(
        partitions,
        output=args.output,
        evidence_output=args.evidence,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
