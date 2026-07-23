"""Validate the Internet Archive source registry and emit a workflow matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fyi_archive.internet_archive_registry import load_registry, workflow_matrix


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("configs/historical/internet_archive_sources.json"),
    )
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        load_registry(args.registry)
        print("Internet Archive source registry: PASS")
    else:
        print(json.dumps(workflow_matrix(args.registry), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
