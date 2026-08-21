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
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from defusedxml import ElementTree


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
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
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


def _morph_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = csv.DictReader(stream)
        output = []
        for row in rows:
            source_url = _url(row.get("request_url") or row.get("url"))
            if not source_url:
                continue
            output.append({
                "source": "morph_io",
                "evidence_role": "authoritative_discovery",
                "capture_required": True,
                "source_url": source_url,
                "source_record_id": str(row.get("request_url") or ""),
                "title": str(row.get("title") or ""),
                "authority": str(row.get("public_body_name") or ""),
                "state": str(row.get("described_state") or row.get("display_status") or ""),
                "observed_at": str(row.get("created_at") or ""),
            })
        return output


def _cdx_rows(path: Path, *, instance_id: str | None = None) -> list[dict[str, Any]]:
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
            record = {
                "source": "internet_archive_cdx",
                "evidence_role": "historical_discovery_candidate",
                "capture_required": True,
                "source_url": source_url,
                "source_record_id": digest,
                "title": "",
                "authority": "",
                "state": "",
                "observed_at": timestamp,
                "archive_digest": digest,
            }
            if instance_id:
                record["instance_id"] = instance_id
            output.append(record)
    return output


def _feed_record(
    *,
    source_url: str,
    source_record_id: str,
    title: str = "",
    authority: str = "",
    state: str = "",
    observed_at: str = "",
    instance_id: str | None = None,
    source: str,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "source": source,
        "evidence_role": "authoritative_discovery",
        "capture_required": True,
        "source_url": source_url,
        "source_record_id": source_record_id,
        "title": title,
        "authority": authority,
        "state": state,
        "observed_at": observed_at,
    }
    if instance_id:
        record["instance_id"] = instance_id
    return record


def _feed_rows(path: Path, *, instance_id: str | None, source: str) -> list[dict[str, Any]]:
    """Normalize an Alaveteli JSON feed or JSONL export."""
    text = path.read_text(encoding="utf-8-sig")
    try:
        payload = json.loads(text)
        raw_entries = payload.get("entries", payload.get("items", payload.get("requests", [])))
    except json.JSONDecodeError:
        raw_entries = [json.loads(line) for line in text.splitlines() if line.strip()]
    if not isinstance(raw_entries, list):
        raise ValueError("Alaveteli feed JSON must contain an entries/items/requests list")
    output = []
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue
        link = str(entry.get("url") or entry.get("link") or entry.get("html_url") or "")
        source_url = _url(link)
        if not source_url:
            continue
        record_id = str(entry.get("id") or entry.get("request_id") or link)
        authority = entry.get("authority") or entry.get("public_body") or ""
        if isinstance(authority, dict):
            authority = authority.get("name") or authority.get("url_name") or ""
        output.append(
            _feed_record(
                source_url=source_url,
                source_record_id=record_id,
                title=str(entry.get("title") or entry.get("name") or ""),
                authority=str(authority),
                state=str(entry.get("state") or entry.get("status") or ""),
                observed_at=str(entry.get("updated") or entry.get("created_at") or ""),
                instance_id=instance_id,
                source=source,
            ),
        )
    return output


def _atom_rows(path: Path, *, instance_id: str | None) -> list[dict[str, Any]]:
    """Normalize an Atom feed export without contacting its source."""
    root = ElementTree.fromstring(path.read_text(encoding="utf-8-sig"))
    output = []
    for entry in root.iter():
        if entry.tag.rsplit("}", 1)[-1] != "entry":
            continue
        link = next(
            (
                str(child.attrib.get("href") or "")
                for child in entry
                if child.tag.rsplit("}", 1)[-1] == "link" and child.attrib.get("href")
            ),
            "",
        )
        source_url = _url(link)
        if not source_url:
            continue
        values = {
            child.tag.rsplit("}", 1)[-1]: (child.text or "").strip()
            for child in entry
            if child.tag.rsplit("}", 1)[-1] in {"id", "title", "updated", "published", "summary"}
        }
        output.append(
            _feed_record(
                source_url=source_url,
                source_record_id=values.get("id", link),
                title=values.get("title", ""),
                observed_at=values.get("updated") or values.get("published", ""),
                instance_id=instance_id,
                source="alaveteli_atom",
            ),
        )
    return output


def _structured_rows(path: Path, *, instance_id: str | None, source: str) -> list[dict[str, Any]]:
    """Normalize a downloaded official dataset or operator export.

    The importer deliberately accepts only local files.  It supports common
    CSV and JSON shapes while requiring a public request URL in each row; this
    avoids turning statistics-only datasets into request records.
    """
    if path.suffix.lower() in {".csv", ".tsv"}:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            raw_entries: list[dict[str, Any]] = list(
                csv.DictReader(
                    stream, dialect="excel-tab" if path.suffix.lower() == ".tsv" else "excel"
                )
            )
    else:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(payload, list):
            raw_entries = payload
        elif isinstance(payload, dict):
            raw_entries = []
            for key in ("records", "requests", "entries", "items", "results", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    raw_entries = value
                    break
                if isinstance(value, dict) and isinstance(value.get("records"), list):
                    raw_entries = value["records"]
                    break
        else:
            raise ValueError("structured historical export must be a JSON object or array")
    output = []
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue
        source_url = _url(
            entry.get("source_url")
            or entry.get("request_url")
            or entry.get("url")
            or entry.get("html_url")
            or entry.get("link")
        )
        if not source_url:
            continue
        authority = (
            entry.get("authority")
            or entry.get("public_body")
            or entry.get("public_body_name")
            or ""
        )
        if isinstance(authority, dict):
            authority = authority.get("name") or authority.get("url_name") or ""
        output.append(
            _feed_record(
                source_url=source_url,
                source_record_id=str(entry.get("id") or entry.get("request_id") or source_url),
                title=str(entry.get("title") or entry.get("subject") or entry.get("name") or ""),
                authority=str(authority),
                state=str(entry.get("state") or entry.get("status") or ""),
                observed_at=str(
                    entry.get("updated") or entry.get("updated_at") or entry.get("created_at") or ""
                ),
                instance_id=instance_id,
                source=source,
            ),
        )
    return output


def load_historical_source(
    path: Path, source_kind: str, *, instance_id: str | None = None
) -> dict[str, Any]:
    """Load one local historical export and return records plus provenance."""
    if source_kind == "morph":
        records = _morph_rows(path)
    elif source_kind == "internet_archive_cdx":
        records = _cdx_rows(path, instance_id=instance_id)
    elif source_kind == "alaveteli_feed_json":
        records = _feed_rows(path, instance_id=instance_id, source=source_kind)
    elif source_kind == "alaveteli_atom":
        records = _atom_rows(path, instance_id=instance_id)
    elif source_kind in {"official_dataset", "operator_export"}:
        records = _structured_rows(path, instance_id=instance_id, source=source_kind)
    else:
        raise ValueError(f"unsupported historical source kind: {source_kind}")
    return {
        "source": source_kind,
        "input_path": str(path),
        "retrieved_at": _retrieved_at(path),
        "sha256": sha256_file(path),
        "record_count": len(records),
        "instance_id": instance_id,
        "records": records,
    }


def merge_historical_sources(inputs: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge candidates while retaining every source's provenance.

    Internet Archive rows are discovery evidence only. They never replace a
    live/official discovery row and never imply that the page was captured.
    """
    by_url: dict[str, dict[str, Any]] = {}
    for document in inputs:
        for record in document["records"]:
            url = record["source_url"]
            current = by_url.get(url)
            if current is None:
                current = dict(record)
                current["evidence_sources"] = []
                current["internet_archive_digests"] = []
                by_url[url] = current
            evidence = {
                "source": record.get("source"),
                "source_record_id": record.get("source_record_id"),
                "observed_at": record.get("observed_at", ""),
                "archive_digest": record.get("archive_digest", ""),
            }
            if evidence not in current["evidence_sources"]:
                current["evidence_sources"].append(evidence)
            digest = str(record.get("archive_digest") or "")
            if digest and digest not in current["internet_archive_digests"]:
                current["internet_archive_digests"].append(digest)
            if (
                current.get("evidence_role") == "historical_discovery_candidate"
                and record.get("evidence_role") != "historical_discovery_candidate"
            ):
                preserved = {key: value for key, value in record.items() if value not in {None, ""}}
                preserved["evidence_sources"] = current["evidence_sources"]
                preserved["internet_archive_digests"] = current["internet_archive_digests"]
                current = preserved
                by_url[url] = current
            current["capture_required"] = True
            current["verification_status"] = "unverified"
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
