"""Write a complete CDX export and immutable acquisition evidence manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from fyi_archive.internet_archive_cdx import CAPTURE_MODES, CDX_ENDPOINT, fetch_complete_cdx


def _write_json(path: Path, value: dict[str, object]) -> None:
    """Write an evidence record, creating only its requested parent directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url-pattern", required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--capture-mode", choices=sorted(CAPTURE_MODES), default="url_index")
    parser.add_argument("--max-runtime-seconds", type=float, default=180.0)
    args = parser.parse_args()
    retrieved_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    base_evidence: dict[str, object] = {
        "provider": "Internet Archive CDX",
        "instance_id": args.instance_id,
        "host": args.host,
        "endpoint": CDX_ENDPOINT,
        "url_pattern": args.url_pattern,
        "capture_mode": args.capture_mode,
        "retrieved_at": retrieved_at,
        "eligible_for_empirical_freeze": False,
        "publication": False,
        "redistribution": False,
    }
    try:
        rows = fetch_complete_cdx(
            args.url_pattern,
            page_size=args.page_size,
            max_pages=args.max_pages,
            capture_mode=args.capture_mode,
            max_runtime_seconds=args.max_runtime_seconds,
        )
    except Exception as error:
        _write_json(
            args.evidence,
            {
                **base_evidence,
                "retrieval_status": "failed",
                "pagination_complete": False,
                "response_sha256": None,
                "record_count": None,
                "failure": {"type": type(error).__name__, "message": str(error)},
            },
        )
        raise
    raw = json.dumps(rows, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(raw, encoding="utf-8")
    evidence = {
        **base_evidence,
        "retrieval_status": "complete",
        "response_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "record_count": len(rows) - 1,
        "pagination_complete": True,
    }
    _write_json(args.evidence, evidence)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
