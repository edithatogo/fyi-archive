"""Build or verify a bounded raw-retention inventory; never publish payloads."""

import argparse
import json
from pathlib import Path

from fyi_archive.raw_batch_retention import build_raw_inventory, verify_raw_inventory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=Path())
    parser.add_argument("--expected-requests", type=int)
    parser.add_argument("--manifest", type=Path, default=Path("raw-package-manifest.json"))
    args = parser.parse_args()
    if args.action == "build":
        if args.expected_requests is None:
            parser.error("--expected-requests is required for build")
        result = build_raw_inventory(args.root, expected_requests=args.expected_requests)
        args.manifest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    else:
        expected = json.loads(args.manifest.read_text(encoding="utf-8"))
        verify_raw_inventory(args.root, expected)
        print("Retained raw package verified; public publication not asserted.")


if __name__ == "__main__":
    main()
