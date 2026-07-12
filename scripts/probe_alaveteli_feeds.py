"""Perform one gentle, provenance-preserving feed compatibility probe per instance."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from fyi_archive.instances import get_instance


def probe_instance(instance_id: str, *, timeout_seconds: float, user_agent: str) -> dict[str, Any]:
    """Check robots and one JSON search-feed URL without retrying."""
    instance = get_instance(instance_id)
    feed_url = instance.search_feed_url()
    checked_at = datetime.now(UTC).isoformat()
    result: dict[str, Any] = {
        "instance_id": instance_id,
        "feed_url": feed_url,
        "checked_at": checked_at,
        "robots_url": f"{instance.capture_base_url()}/robots.txt",
        "robots_status": None,
        "feed_status": None,
        "content_type": "",
        "payload_sha256": "",
        "bytes": 0,
        "json_compatible": False,
        "diagnostic": "",
    }
    headers = {"User-Agent": user_agent, "Accept": "application/json"}
    try:
        with httpx.Client(
            timeout=timeout_seconds, follow_redirects=True, headers=headers
        ) as client:
            robots = client.get(result["robots_url"])
            result["robots_status"] = robots.status_code
            response = client.get(feed_url)
            body = response.content
            result["feed_status"] = response.status_code
            result["content_type"] = response.headers.get("content-type", "")
            result["bytes"] = len(body)
            result["payload_sha256"] = hashlib.sha256(body).hexdigest()
            try:
                json.loads(body)
                result["json_compatible"] = response.is_success
            except json.JSONDecodeError:
                result["diagnostic"] = "response body is not valid JSON"
    except httpx.HTTPError as error:
        result["diagnostic"] = f"{type(error).__name__}: {str(error)[:240]}"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", action="append", required=True)
    parser.add_argument("--delay-seconds", type=float, default=10.0)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    parser.add_argument("--user-agent", default="fyi-archive-feed-probe/1.0 (+read-only research)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.delay_seconds < 0 or args.timeout_seconds <= 0:
        parser.error("delay must be non-negative and timeout must be positive")
    results = []
    for position, instance_id in enumerate(args.instance):
        if position:
            time.sleep(args.delay_seconds)
        results.append(
            probe_instance(
                instance_id, timeout_seconds=args.timeout_seconds, user_agent=args.user_agent
            )
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "schema": "alaveteli-feed-probe-v1",
                "generated_at": datetime.now(UTC).isoformat(),
                "delay_seconds": args.delay_seconds,
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
