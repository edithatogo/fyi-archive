"""Build and validate the normalized archive source graph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fyi_archive.source_graph import build_source_graph, write_source_graph


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    graph = build_source_graph() if args.output is None else write_source_graph(args.output)
    if args.check and (
        graph["counts"]["sites"] != 29 or graph["counts"]["jurisdiction_targets"] != 42
    ):
        raise SystemExit("source graph does not cover the required 29 sites and 42 targets")
    print(
        json.dumps(
            {
                "sites": graph["counts"]["sites"],
                "jurisdiction_targets": graph["counts"]["jurisdiction_targets"],
                "payload_sha256": graph["provenance"]["payload_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
