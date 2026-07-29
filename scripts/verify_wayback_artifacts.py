"""Verify retained Wayback site artifacts and emit a progress index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fyi_archive.wayback_evidence import find_site_count, verify_site_artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", nargs="+", type=Path)
    parser.add_argument("--prior-root", type=Path)
    parser.add_argument("--baseline-root", type=Path)
    parser.add_argument("--default-page-size", type=int, default=1000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sites: list[dict[str, Any]] = []
    for artifact in args.artifacts:
        report = verify_site_artifact(artifact, default_page_size=args.default_page_size)
        site_id = str(report["site_id"])
        for label, root in (("prior", args.prior_root), ("baseline", args.baseline_root)):
            count = find_site_count(root, site_id) if root is not None else None
            report[f"{label}_record_count"] = count
            report[f"{label}_record_delta"] = (
                int(report["record_count"]) - count if count is not None else None
            )
        sites.append(report)
    sites.sort(key=lambda item: str(item["site_id"]))
    payload = {
        "schema": "fyi-archive.wayback-progress-index.v1",
        "site_count": len(sites),
        "complete_site_count": sum(item["complete"] is True for item in sites),
        "record_count": sum(int(item["record_count"]) for item in sites),
        "coverage_percentage": None,
        "coverage_note": "Observed retained records; no corpus denominator is inferred.",
        "sites": sites,
    }
    raw = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding="utf-8")
    print(raw, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
