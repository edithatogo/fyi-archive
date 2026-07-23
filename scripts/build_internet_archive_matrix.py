"""Validate the Internet Archive source registry and emit a workflow matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import jsonschema

from fyi_archive.internet_archive_registry import load_registry, workflow_matrix


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("configs/historical/internet_archive_sources.json"),
    )
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--instance-id")
    parser.add_argument("--capture-mode", choices=["url_index", "all_captures"])
    args = parser.parse_args()
    if args.validate:
        payload = json.loads(args.registry.read_text(encoding="utf-8"))
        schema_path = Path("schemas/internet-archive-source-registry.schema.json")
        jsonschema.validate(payload, json.loads(schema_path.read_text(encoding="utf-8")))
        load_registry(args.registry)
        print("Internet Archive source registry: PASS")
    else:
        print(
            json.dumps(
                workflow_matrix(
                    args.registry,
                    instance_id=args.instance_id,
                    capture_mode=args.capture_mode,
                ),
                separators=(",", ":"),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
