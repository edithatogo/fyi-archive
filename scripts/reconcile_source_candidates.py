"""Classify historical discovery candidates against a captured manifest."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def canonical_url(value: object) -> str:
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    query = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in {"fbclid", "gclid", "mc_cid", "mc_eid"}
    ]
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        path,
        "",
        urlencode(query),
        "",
    ))


def _records(payload: object, *, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [cast("dict[str, Any]", row) for row in value if isinstance(row, dict)]
    return []


def reconcile(index_path: Path, manifest_path: Path) -> dict[str, Any]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates = _records(index, keys=("records",))
    captured = _records(manifest, keys=("requests", "records"))
    captured_urls = {
        canonical_url(row.get("request_url") or row.get("url") or row.get("source_url"))
        for row in captured
    }
    captured_urls.discard("")
    rows = []
    for row in candidates:
        url = canonical_url(row.get("source_url") or row.get("request_url") or row.get("url"))
        if not url:
            continue
        status = "live_captured" if url in captured_urls else "unresolved"
        if row.get("source") == "internet_archive_cdx" and status != "live_captured":
            status = "archive_only_candidate"
        rows.append({
            "canonical_url": url,
            "source": row.get("source", ""),
            "evidence_role": row.get("evidence_role", ""),
            "verification_status": status,
            "archive_digests": row.get("internet_archive_digests", []),
        })
    counts = Counter(row["verification_status"] for row in rows)
    return {
        "schema": "historical-source-reconciliation-v1",
        "candidate_count": len(rows),
        "captured_manifest_count": len(captured),
        "counts": dict(sorted(counts.items())),
        "records": rows,
        "inputs": {
            "historical_source_index": str(index_path),
            "captured_manifest": str(manifest_path),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-source-index", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = reconcile(args.historical_source_index, args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps({
            key: result[key] for key in ("candidate_count", "captured_manifest_count", "counts")
        })
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
