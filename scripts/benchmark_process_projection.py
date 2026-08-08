"""Benchmark a supplied process-event projection without publishing its data."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from fyi_archive.process_projection import build_process_projection, verify_process_projection


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--attachments", type=Path)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()

    started = time.perf_counter()
    try:
        coverage = build_process_projection(
            events_path=args.events,
            output_dir=args.output,
            manifest_path=args.manifest,
            attachments_path=args.attachments,
            snapshot_revision=args.revision,
        )
        verify_process_projection(args.output)
    except Exception as exc:  # noqa: BLE001
        print(f"Error during projection build or verification: {exc}", file=sys.stderr)
        return 1
    elapsed = time.perf_counter() - started
    try:
        digest = hashlib.sha256((args.output / "CHECKSUMS.sha256").read_bytes()).hexdigest()
    except FileNotFoundError as exc:
        print(f"Error: CHECKSUMS.sha256 not found at {args.output}: {exc}", file=sys.stderr)
        return 1
    report = {
        "source_revision": args.revision,
        "elapsed_seconds": round(elapsed, 6),
        "checksums_sha256": digest,
        "coverage": coverage,
        "publication": "none",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
