"""Discover request feeds for the NSW authority queue through fyi-cli."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def discover_requests(
    *,
    queue_path: Path,
    output_path: Path,
    base_url: str,
    db_path: Path,
    delay_seconds: float,
) -> int:
    """Run one rate-limited fyi-cli discovery per NSW authority and deduplicate IDs."""
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    if queue.get("instance_id") != "au-rtk" or queue.get("jurisdiction") != "NSW":
        raise ValueError("NSW queue must be scoped to au-rtk/NSW")
    rows: dict[int, dict[str, object]] = {}
    with tempfile.TemporaryDirectory() as temporary:
        for authority in queue.get("authorities", []):
            slug = str(authority["slug"])
            authority_output = Path(temporary) / f"{slug}.jsonl"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "fyi_system.cli",
                    "discover",
                    "--base-url",
                    base_url,
                    "--authority",
                    slug,
                    "--delay-seconds",
                    str(delay_seconds),
                    "--db",
                    str(db_path),
                    "--output",
                    str(authority_output),
                ],
                check=True,
            )
            if not authority_output.exists():
                continue
            for line in authority_output.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                rows[int(row["request_id"])] = row
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(rows[key], sort_keys=True) + "\n" for key in sorted(rows)),
        encoding="utf-8",
    )
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    args = parser.parse_args()
    print(
        discover_requests(
            queue_path=args.queue,
            output_path=args.output,
            base_url=args.base_url,
            db_path=args.db,
            delay_seconds=args.delay_seconds,
        ),
    )


if __name__ == "__main__":
    main()
