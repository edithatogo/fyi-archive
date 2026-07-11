"""Offline historical-source import for public FOI archive indexes.

This module never contacts a source. Operators provide downloaded Morph CSV or
Internet Archive CDX JSON exports, and the importer records each input's hash,
source label, and local retrieval metadata before producing a deduplicated
index. The result is an evidence layer, not a claim that the corresponding
Right to Know pages or attachments were captured.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a local input file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _retrieved_at(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()


def _url(value: object) -> str:
    candidate = str(value or "").strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return candidate


def _morph_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = csv.DictReader(stream)
        output = []
        for row in rows:
            source_url = _url(row.get("request_url") or row.get("url"))
            if not source_url:
                continue
            output.append(
                {
                    "source": "morph_io",
                    "source_url": source_url,
                    "source_record_id": str(row.get("request_url") or ""),
                    "title": str(row.get("title") or ""),
                    "authority": str(row.get("public_body_name") or ""),
                    "state": str(row.get("described_state") or row.get("display_status") or ""),
                    "observed_at": str(row.get("created_at") or ""),
                }
            )
        return output


def _cdx_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Internet Archive CDX export must be a JSON array")
    rows = payload[1:] if payload and payload[0] == ["original", "timestamp", "digest"] else payload
    output = []
    for row in rows:
        if isinstance(row, dict):
            source_url = _url(row.get("original"))
            timestamp = str(row.get("timestamp") or "")
            digest = str(row.get("digest") or "")
        elif isinstance(row, list) and len(row) >= 1:
            source_url = _url(row[0])
            timestamp = str(row[1]) if len(row) > 1 else ""
            digest = str(row[2]) if len(row) > 2 else ""
        else:
            continue
        if source_url:
            output.append(
                {
                    "source": "internet_archive_cdx",
                    "source_url": source_url,
                    "source_record_id": digest,
                    "title": "",
                    "authority": "",
                    "state": "",
                    "observed_at": timestamp,
                    "archive_digest": digest,
                }
            )
    return output


def load_historical_source(path: Path, source_kind: str) -> dict[str, Any]:
    """Load one local historical export and return records plus provenance."""
    if source_kind == "morph":
        records = _morph_rows(path)
    elif source_kind == "internet_archive_cdx":
        records = _cdx_rows(path)
    else:
        raise ValueError(f"unsupported historical source kind: {source_kind}")
    return {
        "source": source_kind,
        "input_path": str(path),
        "retrieved_at": _retrieved_at(path),
        "sha256": sha256_file(path),
        "record_count": len(records),
        "records": records,
    }


def merge_historical_sources(inputs: list[dict[str, Any]]) -> dict[str, Any]:
    """Deduplicate source records by URL and return an evidence index."""
    by_url: dict[str, dict[str, Any]] = {}
    for document in inputs:
        for record in document["records"]:
            by_url.setdefault(record["source_url"], record)
    records = [by_url[url] for url in sorted(by_url)]
    return {
        "schema": "historical-source-index-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "record_count": len(records),
        "records": records,
        "inputs": [
            {key: value for key, value in document.items() if key != "records"}
            for document in inputs
        ],
    }
