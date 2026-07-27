"""Reconcile a site's public denominator across preservation inventories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fyi_archive.completeness import load_inventory, reconcile_completeness


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--enumerated", type=Path, required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--internet-archive", type=Path, required=True)
    parser.add_argument("--secondary", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    secondary = {}
    for value in args.secondary:
        name, separator, raw_path = value.partition("=")
        if not separator or not name or not raw_path:
            parser.error("--secondary must use NAME=PATH")
        secondary[name] = load_inventory(Path(raw_path))
    report = reconcile_completeness(
        site_id=args.site_id,
        enumerated=load_inventory(args.enumerated),
        primary=load_inventory(args.primary),
        internet_archive=load_inventory(args.internet_archive),
        secondary=secondary,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "site_id": args.site_id,
                "denominator": report["denominator"]["count"],
                "primary_percent": report["channels"]["primary"]["percent"],
                "internet_archive_percent": report["channels"]["internet_archive"]["percent"],
                "complete": report["complete"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
