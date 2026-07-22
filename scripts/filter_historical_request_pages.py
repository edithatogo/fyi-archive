"""Filter an imported CDX index to canonical Alaveteli request pages."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

CANONICAL_REQUEST_PATH = re.compile(r"^/request/[^/?\.]+$")


def is_canonical_request_url(url: str) -> bool:
    """Accept only the request page, excluding JSON, response, and attachment URLs."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(
        CANONICAL_REQUEST_PATH.fullmatch(parsed.path)
    )


def filter_index(index: dict[str, Any]) -> dict[str, Any]:
    records = [
        record
        for record in index.get("records", [])
        if isinstance(record, dict) and is_canonical_request_url(str(record.get("source_url", "")))
    ]
    return {
        **index,
        "schema": "historical-source-index-v1",
        "filter": {
            "name": "canonical_alaveteli_request_pages",
            "excluded": ["attachments", "response paths", "JSON variants", "non-request paths"],
            "input_record_count": len(index.get("records", [])),
            "output_record_count": len(records),
        },
        "records": records,
        "record_count": len(records),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    index = json.loads(args.input.read_text(encoding="utf-8"))
    output = filter_index(index)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"canonical request pages={output['record_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
