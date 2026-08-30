"""Verify raw capture bytes before a temporary artifact can earn queue credit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, BinaryIO

from warcio.archiveiterator import ArchiveIterator

from fyi_archive.archive_package import sha256_file

MAX_RAW_BYTES = 2 * 1024**3
MAX_RAW_FILES = 10000


def _digest_stream(stream: BinaryIO) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        size += len(chunk)
        if size > MAX_RAW_BYTES:
            raise ValueError("raw response exceeds retention byte budget")
        digest.update(chunk)
    return digest.hexdigest(), size


def _safe_file(root: Path, path: Path) -> Path:
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("missing or unsafe raw object")
    return path


def _warc_resources(root: Path) -> dict[str, tuple[str, int]]:
    result: dict[str, tuple[str, int]] = {}
    total = 0
    for path in sorted((root / "data/warc").glob("*.warc.gz")):
        with _safe_file(root, path).open("rb") as stream:
            for record in ArchiveIterator(stream):
                if record.rec_type != "response":
                    continue
                identity = record.rec_headers.get_header("WARC-Record-ID")
                if not identity or identity in result:
                    raise ValueError("missing or duplicate WARC record identity")
                digest, size = _digest_stream(record.content_stream())
                total += size
                if total > MAX_RAW_BYTES:
                    raise ValueError("raw batch exceeds decompressed byte budget")
                result[identity] = (digest, size)
    return result


def _check_request(root: Path, request: Path, warc: dict[str, tuple[str, int]]) -> set[str]:
    metadata = _safe_file(root, request.parent / "snapshot_meta.json")
    resources = json.loads(metadata.read_text(encoding="utf-8"))["resources"]
    if not {"json", "html"}.issubset({row["kind"] for row in resources}):
        raise ValueError("raw JSON and HTML response evidence required")
    identities: set[str] = set()
    for row in resources:
        identity = row["warc_record_id"]
        expected = (row["sha256"], row["size"])
        if warc.get(identity) != expected:
            raise ValueError("missing or corrupt WARC response")
        identities.add(identity)
        path = None
        if row["kind"] == "html":
            path = request.parent / "page.html"
        elif row["kind"] == "attachment":
            relative = Path(row["path"])
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or relative.parts[:2] != ("data", "attachments")
            ):
                raise ValueError("unsafe attachment path")
            path = root / relative
        if path is not None:
            _safe_file(root, path)
            if (sha256_file(path), path.stat().st_size) != expected:
                raise ValueError("raw object digest or size mismatch")
    return identities


def build_raw_inventory(root: Path, *, expected_requests: int) -> dict[str, Any]:
    """Require reconstructable original responses, not a manifest-only artifact."""
    requests = sorted((root / "data/raw/requests").glob("*/*/request.json"))
    if expected_requests < 1 or len(requests) != expected_requests:
        raise ValueError("raw request count does not match the credited batch")
    paths = []
    total = 0
    for directory in (root / "data", root / "dist/site_snapshots"):
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError("unsafe symlink in raw package")
            if path.is_dir():
                continue
            _safe_file(root, path)
            total += path.stat().st_size
            paths.append(path)
            if len(paths) > MAX_RAW_FILES or total > MAX_RAW_BYTES:
                raise ValueError("raw package exceeds retention budget")
    warc = _warc_resources(root)
    required: set[str] = set()
    for request in requests:
        required.update(_check_request(root, request, warc))
    return {
        "schema": "fyi-archive.raw-batch-inventory.v1",
        "request_count": len(requests),
        "warc_resource_count": len(required),
        "total_bytes": total,
        "public_publication_verified": False,
        "storage_scope": "temporary GitHub artifact; durable publication still required",
        "files": [
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
            for path in paths
        ],
    }


def verify_raw_inventory(root: Path, expected: dict[str, Any]) -> None:
    """Rebuild the inventory from freshly downloaded bytes and compare exactly."""
    actual = build_raw_inventory(root, expected_requests=expected["request_count"])
    if actual != expected:
        raise ValueError("restored raw package differs from pre-upload inventory")
