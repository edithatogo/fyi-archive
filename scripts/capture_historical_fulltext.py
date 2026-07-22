"""Capture bounded Internet Archive replay text with immutable provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


def capture(index: dict[str, Any], *, instance_id: str, delay: float, timeout: float) -> dict[str, Any]:
    records = list(index.get("records") or [])
    output = []
    for number, record in enumerate(records):
        source_url = str(record.get("source_url") or "")
        timestamp = str(record.get("observed_at") or "")
        replay = f"https://web.archive.org/web/{timestamp}id_/{source_url}" if timestamp and source_url else ""
        item: dict[str, Any] = {"source_url": source_url, "replay_url": replay, "archive_timestamp": timestamp, "archive_digest": record.get("archive_digest"), "instance_id": instance_id}
        try:
            request = urllib.request.Request(replay, headers={"User-Agent": "fyi-archive-fulltext-replay/1.0"})  # noqa: S310
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                raw = response.read(8 * 1024 * 1024)
            html = raw.decode("utf-8", errors="replace")
            text = " ".join(BeautifulSoup(html, "html.parser").get_text(" ").split())
            item.update({"status": "captured", "byte_count": len(raw), "html_sha256": hashlib.sha256(raw).hexdigest(), "text": text, "text_sha256": hashlib.sha256(text.encode()).hexdigest()})
        except Exception as error:  # noqa: BLE001
            item.update({"status": "failed", "diagnostic": str(error)})
        output.append(item)
        if number + 1 < len(records):
            time.sleep(max(0.0, delay))
    return {"schema": "fyi-archive.historical-fulltext.v1", "generated_at": datetime.now(UTC).isoformat(), "instance_id": instance_id, "rights_eligible": False, "annotation_execution_authorized": False, "record_count": len(output), "captured_count": sum(item["status"] == "captured" for item in output), "records": output}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    result = capture(json.loads(args.index.read_text(encoding="utf-8")), instance_id=args.instance_id, delay=args.delay, timeout=args.timeout)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
