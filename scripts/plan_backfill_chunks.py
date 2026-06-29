#!/usr/bin/env python3
"""Plan bounded historical backfill ID chunks for GitHub Actions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def plan_chunks(
    *,
    id_from: int,
    id_to: int,
    chunk_size: int,
    max_chunks: int | None = None,
) -> dict[str, list[dict[str, str]]]:
    """Build a GitHub Actions matrix for inclusive request-ID chunks."""
    if id_from < 1 or id_to < 1:
        msg = "id_from and id_to must be positive"
        raise ValueError(msg)
    if id_from > id_to:
        msg = "id_from must be <= id_to"
        raise ValueError(msg)
    if chunk_size < 1:
        msg = "chunk_size must be positive"
        raise ValueError(msg)

    chunks = []
    current = id_from
    while current <= id_to:
        if max_chunks is not None and len(chunks) >= max_chunks:
            break
        chunk_end = min(current + chunk_size - 1, id_to)
        chunks.append(
            {
                "id_from": str(current),
                "id_to": str(chunk_end),
                "label": f"{current}-{chunk_end}",
            },
        )
        current = chunk_end + 1
    return {"include": chunks}


def main() -> None:
    """Parse CLI arguments and write a chunk matrix."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--id-from", type=int, required=True)
    parser.add_argument("--id-to", type=int, required=True)
    parser.add_argument("--chunk-size", type=int, required=True)
    parser.add_argument("--max-chunks", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    matrix = plan_chunks(
        id_from=args.id_from,
        id_to=args.id_to,
        chunk_size=args.chunk_size,
        max_chunks=args.max_chunks,
    )
    payload = json.dumps(matrix, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
