"""Build an offline, provenance-preserving historical source index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fyi_archive.historical_sources import load_historical_source, merge_historical_sources


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--morph-csv", type=Path)
    parser.add_argument("--internet-archive-cdx", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = []
    if args.morph_csv:
        inputs.append(load_historical_source(args.morph_csv, "morph"))
    if args.internet_archive_cdx:
        inputs.append(load_historical_source(args.internet_archive_cdx, "internet_archive_cdx"))
    if not inputs:
        parser.error("provide --morph-csv and/or --internet-archive-cdx")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(merge_historical_sources(inputs), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
