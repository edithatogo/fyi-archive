"""Enrich a historical CDX index from Internet Archive replay pages only."""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fyi_archive.historical_core import (
    archive_replay_url,
    failed_archived_request,
    parse_archived_request,
)
from fyi_archive.historical_sources import sha256_file


def enrich(
    index: dict[str, Any],
    *,
    instance_id: str,
    limit: int,
    delay_seconds: float,
    user_agent: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Fetch a bounded number of replay pages and extract core metadata."""
    records = list(index.get("records") or [])[: max(0, limit)]
    enriched: list[dict[str, Any]] = []
    for number, record in enumerate(records):
        source_url = str(record.get("source_url") or "")
        timestamp = str(record.get("observed_at") or "")
        digest = str(record.get("archive_digest") or record.get("source_record_id") or "")
        replay_url = archive_replay_url(source_url, timestamp) if timestamp else ""
        if not replay_url:
            enriched.append(
                failed_archived_request(
                    source_url=source_url,
                    archive_url="",
                    archive_timestamp=timestamp,
                    archive_digest=digest,
                    diagnostic="missing CDX timestamp",
                    instance_id=instance_id,
                )
            )
            continue
        try:
            request = urllib.request.Request(  # noqa: S310
                replay_url, headers={"User-Agent": user_agent}
            )
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                html = response.read(2 * 1024 * 1024).decode("utf-8", errors="replace")
            enriched.append(
                parse_archived_request(
                    html,
                    source_url=source_url,
                    archive_url=replay_url,
                    archive_timestamp=timestamp,
                    archive_digest=digest,
                    instance_id=instance_id,
                )
            )
        except Exception as error:  # noqa: BLE001
            enriched.append(
                failed_archived_request(
                    source_url=source_url,
                    archive_url=replay_url,
                    archive_timestamp=timestamp,
                    archive_digest=digest,
                    diagnostic=str(error),
                    instance_id=instance_id,
                )
            )
        if number + 1 < len(records):
            time.sleep(max(0.0, delay_seconds))
    return {
        "schema": "historical-core-index-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "instance_id": instance_id,
        "input_record_count": len(index.get("records") or []),
        "processed_record_count": len(records),
        "extracted_record_count": sum(
            record.get("extraction_status") == "extracted" for record in enriched
        ),
        "records": enriched,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--delay-seconds", type=float, default=3.0)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    parser.add_argument("--user-agent", default="fyi-archive-historical-core/1.0")
    args = parser.parse_args()
    index = json.loads(args.historical_index.read_text(encoding="utf-8"))
    output = enrich(
        index,
        instance_id=args.instance_id,
        limit=args.limit,
        delay_seconds=args.delay_seconds,
        user_agent=args.user_agent,
        timeout_seconds=args.timeout_seconds,
    )
    output["input_sha256"] = sha256_file(args.historical_index)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
