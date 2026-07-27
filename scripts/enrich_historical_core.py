"""Enrich a bounded historical CDX index from Internet Archive replay pages only."""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fyi_archive.historical_core import (
    archive_replay_url,
    failed_archived_request,
    parse_archived_request,
)
from fyi_archive.historical_sources import sha256_file

FetchReplay = Callable[[str, str, float], bytes]


def _fetch_replay(replay_url: str, user_agent: str, timeout_seconds: float) -> bytes:
    request = urllib.request.Request(replay_url, headers={"User-Agent": user_agent})  # noqa: S310
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        return response.read(2 * 1024 * 1024)


def enrich(
    index: dict[str, Any],
    *,
    instance_id: str,
    limit: int,
    start_offset: int = 0,
    retries: int = 0,
    retry_delay_seconds: float = 3.0,
    delay_seconds: float,
    user_agent: str,
    timeout_seconds: float,
    fetch_replay: FetchReplay | None = None,
) -> dict[str, Any]:
    """Fetch one deterministic, bounded replay slice and extract core metadata."""
    if start_offset < 0:
        raise ValueError("start_offset must be non-negative")
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if retries < 0:
        raise ValueError("retries must be non-negative")

    source_records = list(index.get("records") or [])
    records = source_records[start_offset : start_offset + limit]
    fetch = fetch_replay or _fetch_replay
    enriched: list[dict[str, Any]] = []
    for number, record in enumerate(records):
        source_url = str(record.get("source_url") or "")
        timestamp = str(record.get("observed_at") or "")
        digest = str(record.get("archive_digest") or record.get("source_record_id") or "")
        replay_url = archive_replay_url(source_url, timestamp) if timestamp else ""
        if not replay_url:
            item = failed_archived_request(
                source_url=source_url,
                archive_url="",
                archive_timestamp=timestamp,
                archive_digest=digest,
                diagnostic="missing CDX timestamp",
                instance_id=instance_id,
            )
            item["attempt_count"] = 0
            enriched.append(item)
            continue

        last_error: Exception | None = None
        for attempt in range(1, retries + 2):
            try:
                raw = fetch(replay_url, user_agent, timeout_seconds)
                item = parse_archived_request(
                    raw.decode("utf-8", errors="replace"),
                    source_url=source_url,
                    archive_url=replay_url,
                    archive_timestamp=timestamp,
                    archive_digest=digest,
                    instance_id=instance_id,
                )
                item["attempt_count"] = attempt
                enriched.append(item)
                break
            except Exception as error:  # noqa: BLE001
                last_error = error
                if attempt <= retries:
                    time.sleep(max(0.0, retry_delay_seconds))
        else:
            item = failed_archived_request(
                source_url=source_url,
                archive_url=replay_url,
                archive_timestamp=timestamp,
                archive_digest=digest,
                diagnostic=str(last_error),
                instance_id=instance_id,
            )
            item["attempt_count"] = retries + 1
            enriched.append(item)

        if number + 1 < len(records):
            time.sleep(max(0.0, delay_seconds))
    return {
        "schema": "historical-core-index-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "instance_id": instance_id,
        "input_record_count": len(source_records),
        "start_offset": start_offset,
        "processed_record_count": len(records),
        "retries": retries,
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
    parser.add_argument("--start-offset", type=int, default=0)
    parser.add_argument("--retries", type=int, default=0)
    parser.add_argument("--retry-delay-seconds", type=float, default=3.0)
    parser.add_argument("--delay-seconds", type=float, default=3.0)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    parser.add_argument("--user-agent", default="fyi-archive-historical-core/1.0")
    args = parser.parse_args()
    index = json.loads(args.historical_index.read_text(encoding="utf-8"))
    output = enrich(
        index,
        instance_id=args.instance_id,
        limit=args.limit,
        start_offset=args.start_offset,
        retries=args.retries,
        retry_delay_seconds=args.retry_delay_seconds,
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
