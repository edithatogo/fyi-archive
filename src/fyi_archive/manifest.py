"""Manifest assembly for derived fyi.org.nz records."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from fyi_archive.version import __version__

SOURCE_URL = "https://fyi.org.nz/"


def canonical_sha256(data: dict[str, Any]) -> str:
    """Hash a record with stable JSON ordering."""
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_request_record(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize one derived record into manifest shape."""
    request_id = int(data.get("request_id") or data["id"])
    normalized = {
        "request_id": request_id,
        "url_title": str(data.get("url_title") or f"request-{request_id}"),
        "title": str(data.get("title") or ""),
        "authority": normalize_authority(data.get("authority") or data.get("public_body")),
        "state": str(data.get("state") or ""),
        "html_captured": bool(data.get("html_captured", False)),
        "attachments": data.get("attachments") or [],
        "warc_record_ids": data.get("warc_record_ids") or [],
        "license": data.get("license"),
        "attribution": data.get("attribution"),
        "first_seen": data.get("first_seen"),
        "last_updated": data.get("last_updated"),
    }
    normalized["content_sha256"] = str(data.get("content_sha256") or canonical_sha256(normalized))
    return normalized


def normalize_authority(value: object) -> str:
    """Normalize scalar or FYI object authority values."""
    if isinstance(value, dict):
        return str(value.get("url_name") or value.get("name") or value.get("id") or "")
    return str(value or "")


def load_request_directory_record(request_json_path: Path) -> dict[str, Any]:
    """Load a fyi-cli derived request directory into manifest shape."""
    request_dir = request_json_path.parent
    data = json.loads(request_json_path.read_text(encoding="utf-8"))
    attachments_path = request_dir / "attachments.json"
    snapshot_meta_path = request_dir / "snapshot_meta.json"
    attachments = (
        json.loads(attachments_path.read_text(encoding="utf-8"))
        if attachments_path.exists()
        else []
    )
    resources = []
    if snapshot_meta_path.exists():
        resources = (
            json.loads(snapshot_meta_path.read_text(encoding="utf-8")).get("resources") or []
        )
    data["html_captured"] = (request_dir / "page.html").exists()
    data["attachments"] = attachments
    data["warc_record_ids"] = [
        str(resource["warc_record_id"]) for resource in resources if resource.get("warc_record_id")
    ]
    return normalize_request_record(data)


def load_derived_records(derived_dir: Path) -> list[dict[str, Any]]:
    """Load derived JSON records from a directory."""
    records = []
    for path in sorted(derived_dir.glob("*.json")):
        records.append(normalize_request_record(json.loads(path.read_text(encoding="utf-8"))))
    for path in sorted(derived_dir.glob("**/request.json")):
        records.append(load_request_directory_record(path))
    return records


def load_manifest_records(manifest_path: Path) -> list[dict[str, Any]]:
    """Load request records from an existing manifest."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    return list(manifest["requests"])


def merge_manifest_records(manifest_paths: list[Path]) -> list[dict[str, Any]]:
    """Merge manifests by request ID, with later manifests replacing earlier ones."""
    by_request_id: dict[int, dict[str, Any]] = {}
    for manifest_path in manifest_paths:
        for record in load_manifest_records(manifest_path):
            by_request_id[int(record["request_id"])] = record
    return [by_request_id[request_id] for request_id in sorted(by_request_id)]


def build_manifest(records: list[dict[str, Any]], fyi_cli_version: str) -> dict[str, Any]:
    """Build a manifest document."""
    return {
        "meta": {
            "generated_at": datetime.now(UTC).isoformat(),
            "source": SOURCE_URL,
            "version": __version__,
            "record_count": len(records),
            "schema": "schemas/manifest.schema.json",
            "fyi_cli_version": fyi_cli_version,
        },
        "requests": records,
    }


def validate_manifest(manifest: dict[str, Any]) -> None:
    """Validate the subset required by schemas/manifest.schema.json."""
    meta = manifest.get("meta")
    requests = manifest.get("requests")
    if not isinstance(meta, dict) or not isinstance(requests, list):
        msg = "Manifest must contain object 'meta' and array 'requests'"
        raise ValueError(msg)
    if meta.get("source") != SOURCE_URL:
        msg = "Manifest source must be https://fyi.org.nz/"
        raise ValueError(msg)
    if meta.get("record_count") != len(requests):
        msg = "Manifest record_count does not match request count"
        raise ValueError(msg)
    for record in requests:
        if not isinstance(record.get("request_id"), int) or record["request_id"] < 1:
            msg = "Manifest request_id must be a positive integer"
            raise ValueError(msg)
        digest = record.get("content_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            msg = "Manifest content_sha256 must be a 64-character hex string"
            raise ValueError(msg)


def write_manifest_outputs(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    parquet_path: Path,
    authorities_path: Path,
) -> None:
    """Write JSON, Parquet, and authority summary outputs."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    requests = manifest["requests"]
    pl.DataFrame(requests).write_parquet(parquet_path)

    authorities = sorted(
        {record.get("authority", "") for record in requests if record.get("authority")}
    )
    authorities_path.write_text(
        json.dumps({"authorities": authorities}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def assemble_manifest(
    *,
    derived_dir: Path,
    manifest_path: Path,
    parquet_path: Path,
    authorities_path: Path,
    fyi_cli_version: str,
) -> dict[str, Any]:
    """Assemble and write the latest manifest from derived records."""
    records = load_derived_records(derived_dir)
    manifest = build_manifest(records, fyi_cli_version)
    validate_manifest(manifest)
    write_manifest_outputs(
        manifest=manifest,
        manifest_path=manifest_path,
        parquet_path=parquet_path,
        authorities_path=authorities_path,
    )
    return manifest


def merge_manifests(
    *,
    manifest_paths: list[Path],
    manifest_path: Path,
    parquet_path: Path,
    authorities_path: Path,
    fyi_cli_version: str,
) -> dict[str, Any]:
    """Merge existing manifest JSON files and write consolidated outputs."""
    records = merge_manifest_records(manifest_paths)
    manifest = build_manifest(records, fyi_cli_version)
    validate_manifest(manifest)
    write_manifest_outputs(
        manifest=manifest,
        manifest_path=manifest_path,
        parquet_path=parquet_path,
        authorities_path=authorities_path,
    )
    return manifest
