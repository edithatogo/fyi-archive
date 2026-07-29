"""Build a deterministic fyi-cli queue from a completed reconciled source inventory."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlparse


def request_slug(url: object) -> str:
    path = urlparse(str(url or "")).path.rstrip("/")
    prefix = "/request/"
    if not path.startswith(prefix):
        return ""
    slug = path.removeprefix(prefix)
    # HTML and JSON representations identify the same logical request.
    if slug.endswith(".json"):
        slug = slug.removesuffix(".json")
    return slug if slug and "/" not in slug else ""


def build_queue(
    index: Mapping[str, object], retrieval: Mapping[str, object]
) -> list[dict[str, str]]:
    if retrieval.get("retrieval_status") != "complete" or not retrieval.get("pagination_complete"):
        raise ValueError("reconciled source inventory is incomplete")
    records = index.get("records")
    if not isinstance(records, list):
        raise ValueError("source index has no records")
    queue: dict[str, dict[str, str]] = {}
    for row in records:
        if not isinstance(row, dict):
            continue
        source_url = str(row.get("source_url") or "")
        slug = request_slug(source_url)
        if not slug:
            continue
        candidate = {"request_id": slug, "url_title": slug, "source_url": source_url}
        existing = queue.get(slug)
        # Prefer the canonical HTML URL when both representations are present.
        if existing is None or str(existing["source_url"]).endswith(".json"):
            queue[slug] = candidate
    if not queue:
        raise ValueError("completed source inventory has no canonical request URLs")
    return [queue[key] for key in sorted(queue)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-index", type=Path, required=True)
    parser.add_argument("--retrieval-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    queue = build_queue(
        json.loads(args.source_index.read_text(encoding="utf-8")),
        json.loads(args.retrieval_evidence.read_text(encoding="utf-8")),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in queue), encoding="utf-8"
    )
    print(json.dumps({"queue_count": len(queue), "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
