"""Write a complete CDX export and immutable acquisition evidence manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from fyi_archive.internet_archive_cdx import CDX_ENDPOINT, fetch_complete_cdx


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url-pattern", required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--max-pages", type=int, default=100)
    args = parser.parse_args()
    rows = fetch_complete_cdx(args.url_pattern, page_size=args.page_size, max_pages=args.max_pages)
    raw = json.dumps(rows, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(raw, encoding="utf-8")
    evidence = {
        "provider": "Internet Archive CDX",
        "instance_id": args.instance_id,
        "host": args.host,
        "endpoint": CDX_ENDPOINT,
        "url_pattern": args.url_pattern,
        "retrieved_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "response_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "record_count": len(rows) - 1,
        "pagination_complete": True,
        "eligible_for_empirical_freeze": False,
        "publication": False,
        "redistribution": False,
    }
    args.evidence.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
