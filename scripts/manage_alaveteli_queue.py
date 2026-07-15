"""Merge discovered Alaveteli requests with durable capture state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict) or "request_id" not in value:
            raise ValueError(f"{path}:{line_number} must contain an object with request_id")
        rows.append(value)
    return rows


def _request_key(value: object) -> str:
    return str(value)


def _completed_ids(path: Path) -> set[str]:
    return {
        _request_key(row.get("request_id"))
        for row in _load_jsonl(path)
        if row.get("status") == "completed"
    }


def merge_queue(*, queue: Path, ledger: Path, incoming: Path | None, output: Path) -> dict[str, int | bool]:
    """Merge new discovery rows and remove only ledger-verified completions."""
    merged: dict[str, dict[str, Any]] = {}
    for row in _load_jsonl(queue) + (_load_jsonl(incoming) if incoming else []):
        merged[_request_key(row["request_id"])] = row
    completed = _completed_ids(ledger)
    pending = [row for key, row in merged.items() if key not in completed]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in pending),
        encoding="utf-8",
    )
    return {
        "discovered": len(merged),
        "completed": len(completed),
        "pending": len(pending),
        "queue_empty": not pending,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--incoming", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(merge_queue(**vars(args)), sort_keys=True))


if __name__ == "__main__":
    main()
