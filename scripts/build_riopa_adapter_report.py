#!/usr/bin/env python3
"""Build the language-neutral fyi-archive to RIOPA adapter report."""

from __future__ import annotations

import argparse
from pathlib import Path

from fyi_archive.riopa_adapter import write_adapter_report


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mapping",
        type=Path,
        default=Path("conformance/riopa/v1/fyi-archive-mapping.json"),
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("conformance/riopa/v1/native-evidence-fixture.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("conformance/riopa/v1/adapter-report.json"),
    )
    return parser.parse_args()


def main() -> None:
    """Write the deterministic adapter report."""
    args = parse_args()
    write_adapter_report(
        mapping_path=args.mapping,
        fixture_path=args.fixture,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
