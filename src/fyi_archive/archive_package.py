"""Deterministic immutable archive packages and durable local indexes."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal, TypedDict, cast
from urllib.parse import urlsplit

from fyi_archive.instances import get_instance

PACKAGE_SCHEMA_VERSION = "1.0.0"
PACKAGE_METADATA_SCHEMA = "fyi-archive.archive-package-metadata.v1"
INDEX_SCHEMA_VERSION = "1.0.0"
CATALOG_SCHEMA_VERSION = "1.0.0"
EVENT_ORDER_KEY = "source_sequence_then_event_id"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
PackageKind = Literal["snapshot", "delta"]
FileRole = Literal["cases", "events", "attachments", "other"]


class PackageFile(TypedDict):
    """One checksummed package file compatible with foi-process intake."""

    order: int
    path: str
    role: FileRole
    media_type: str
    sha256: str
    byte_count: int
    row_count: int | None


class PackageCounts(TypedDict):
    """Aggregate package row and file counts."""

    file_count: int
    case_count: int
    event_count: int
    attachment_count: int


class PackageIndexEntry(TypedDict):
    """Compact revision entry for durable indexes."""

    archive_revision: int
    package_id: str
    manifest_sha256: str
    takedown_revision: str
    repository: str
    repository_revision: str
    package_kind: PackageKind
    base_archive_revision: int | None
    package_path: str
    counts: PackageCounts


@dataclass(frozen=True, slots=True)
class PackageInputs:
    """Transport-independent inputs for one package revision."""

    instance_id: str
    archive_revision: int
    repository: str
    repository_revision: str
    cases_path: Path
    events_path: Path
    attachments_path: Path
    takedown_inventory_path: Path
    provenance_path: Path
    retention_path: Path
    package_kind: PackageKind = "snapshot"
    base_archive_revision: int | None = None


def canonical_json(value: object) -> bytes:
    """Return stable UTF-8 JSON bytes for package identity and indexes."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    """Return a lowercase SHA-256 digest."""
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash a file without loading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return document


def _read_ndjson(path: Path, *, label: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"missing {label} file: {path}")
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid {label} JSON at row {line_number}") from error
            if not isinstance(row, dict):
                raise ValueError(f"{label} row {line_number} must be a JSON object")
            rows.append(row)
    return rows


def _event_key(row: dict[str, Any], row_number: int) -> tuple[int, str]:
    event_id = row.get("event_id")
    position = row.get("position")
    sequence: object = row.get("source_sequence")
    if isinstance(position, dict):
        sequence = position.get("sequence", sequence)
    if not isinstance(event_id, str) or not event_id:
        raise ValueError(f"event row {row_number} requires event_id")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
        raise ValueError(f"event row {row_number} requires a non-negative source sequence")
    return sequence, event_id


def _validate_event_order(rows: list[dict[str, Any]]) -> tuple[int | None, int | None]:
    keys = [_event_key(row, index) for index, row in enumerate(rows, 1)]
    if any(current <= previous for previous, current in pairwise(keys)):
        raise ValueError("events must be strictly ordered by source sequence then event_id")
    if not keys:
        return None, None
    return keys[0][0], keys[-1][0]


def _validate_repository(instance_id: str, repository: str, revision: str) -> None:
    parsed = urlsplit(repository)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("repository must be an HTTPS archive transport URI")
    source_host = urlsplit(get_instance(instance_id).source).hostname
    if parsed.hostname == source_host:
        raise ValueError("repository must not be the source-site transport")
    if not HEX40.fullmatch(revision):
        raise ValueError("repository_revision must be a full lowercase 40-character commit")


def _validate_inputs(inputs: PackageInputs, index: dict[str, Any] | None) -> None:
    get_instance(inputs.instance_id)
    if inputs.archive_revision < 1:
        raise ValueError("archive_revision must be positive")
    _validate_repository(inputs.instance_id, inputs.repository, inputs.repository_revision)
    if inputs.package_kind == "snapshot":
        if inputs.base_archive_revision is not None:
            raise ValueError("snapshot packages must not declare base_archive_revision")
    elif inputs.package_kind == "delta":
        if inputs.base_archive_revision is None or inputs.base_archive_revision < 1:
            raise ValueError("delta packages require a positive base_archive_revision")
    else:
        raise ValueError("package_kind must be snapshot or delta")

    revisions = [] if index is None else cast("list[dict[str, Any]]", index.get("revisions", []))
    if revisions:
        latest = revisions[-1]
        latest_revision = int(latest["archive_revision"])
        if inputs.archive_revision <= latest_revision:
            return
        if inputs.package_kind == "delta" and inputs.base_archive_revision != latest_revision:
            raise ValueError("delta base_archive_revision must equal the latest indexed revision")
    elif inputs.package_kind == "delta":
        raise ValueError("the first package for an instance must be a snapshot")


def _atomic_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def _canonical_sidecar(source: Path, destination: Path, *, label: str) -> dict[str, Any]:
    document = _load_json_object(source, label=label)
    destination.write_bytes(canonical_json(document) + b"\n")
    return document


def _file_entry(
    *, order: int, path: Path, package_root: Path, role: FileRole, row_count: int | None
) -> PackageFile:
    return {
        "order": order,
        "path": path.relative_to(package_root).as_posix(),
        "role": role,
        "media_type": "application/x-ndjson" if role != "other" else "application/json",
        "sha256": sha256_file(path),
        "byte_count": path.stat().st_size,
        "row_count": row_count,
    }


def _identity_material(manifest: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in manifest.items() if key != "package_id"}


def package_id(manifest: dict[str, Any]) -> str:
    """Derive the foi-process-compatible package identity."""
    return sha256_bytes(canonical_json(_identity_material(manifest)))


def _load_index(output_root: Path, instance_id: str) -> dict[str, Any] | None:
    path = output_root / "indexes" / instance_id / "index.json"
    if not path.exists():
        return None
    document = _load_json_object(path, label="package index")
    if document.get("schema_version") != INDEX_SCHEMA_VERSION:
        raise ValueError("unsupported package index schema_version")
    if document.get("instance_id") != instance_id:
        raise ValueError("package index instance mismatch")
    revisions = document.get("revisions")
    if not isinstance(revisions, list):
        raise ValueError("package index revisions must be an array")
    return document


def _build_staging(
    inputs: PackageInputs, staging: Path
) -> tuple[dict[str, Any], PackageIndexEntry]:
    cases = _read_ndjson(inputs.cases_path, label="cases")
    events = _read_ndjson(inputs.events_path, label="events")
    attachments = _read_ndjson(inputs.attachments_path, label="attachments")
    first_sequence, last_sequence = _validate_event_order(events)
    provenance = _load_json_object(inputs.provenance_path, label="provenance")
    retention = _load_json_object(inputs.retention_path, label="retention")
    if not isinstance(retention.get("status"), str) or not retention["status"]:
        raise ValueError("retention metadata requires a non-empty status")

    metadata_dir = staging / "metadata"
    metadata_dir.mkdir()
    shutil.copyfile(inputs.cases_path, staging / "cases.ndjson")
    shutil.copyfile(inputs.events_path, staging / "events.ndjson")
    shutil.copyfile(inputs.attachments_path, staging / "attachments.ndjson")
    shutil.copyfile(inputs.takedown_inventory_path, metadata_dir / "takedown-inventory.ndjson")
    _canonical_sidecar(inputs.provenance_path, metadata_dir / "provenance.json", label="provenance")
    _canonical_sidecar(inputs.retention_path, metadata_dir / "retention.json", label="retention")

    takedown_revision = sha256_file(metadata_dir / "takedown-inventory.ndjson")
    package_metadata = {
        "schema": PACKAGE_METADATA_SCHEMA,
        "package_kind": inputs.package_kind,
        "base_archive_revision": inputs.base_archive_revision,
        "archive_revision": inputs.archive_revision,
        "takedown_revision": takedown_revision,
        "ordering": {"event_key": EVENT_ORDER_KEY},
        "provenance": provenance,
        "retention": retention,
        "compatible_contracts": {
            "foi_process_archive_package": PACKAGE_SCHEMA_VERSION,
            "fyi_cli_process_event": "1.0.0",
        },
    }
    (metadata_dir / "package-metadata.json").write_bytes(canonical_json(package_metadata) + b"\n")

    declared = [
        (staging / "cases.ndjson", "cases", len(cases)),
        (staging / "events.ndjson", "events", len(events)),
        (staging / "attachments.ndjson", "attachments", len(attachments)),
        (metadata_dir / "package-metadata.json", "other", None),
        (metadata_dir / "provenance.json", "other", None),
        (metadata_dir / "retention.json", "other", None),
        (metadata_dir / "takedown-inventory.ndjson", "other", None),
    ]
    files = [
        _file_entry(
            order=order,
            path=path,
            package_root=staging,
            role=cast("FileRole", role),
            row_count=row_count,
        )
        for order, (path, role, row_count) in enumerate(declared, 1)
    ]
    counts: PackageCounts = {
        "file_count": len(files),
        "case_count": len(cases),
        "event_count": len(events),
        "attachment_count": len(attachments),
    }
    manifest: dict[str, Any] = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "package_id": "0" * 64,
        "instance_id": inputs.instance_id,
        "archive_revision": inputs.archive_revision,
        "takedown_revision": takedown_revision,
        "source": {"repository": inputs.repository, "revision": inputs.repository_revision},
        "ordering": {
            "event_key": EVENT_ORDER_KEY,
            "first_source_sequence": first_sequence,
            "last_source_sequence": last_sequence,
        },
        "counts": counts,
        "files": files,
    }
    manifest["package_id"] = package_id(manifest)
    manifest_bytes = canonical_json(manifest) + b"\n"
    (staging / "archive-package.json").write_bytes(manifest_bytes)
    entry: PackageIndexEntry = {
        "archive_revision": inputs.archive_revision,
        "package_id": manifest["package_id"],
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "takedown_revision": takedown_revision,
        "repository": inputs.repository,
        "repository_revision": inputs.repository_revision,
        "package_kind": inputs.package_kind,
        "base_archive_revision": inputs.base_archive_revision,
        "package_path": f"packages/{inputs.instance_id}/{inputs.archive_revision:020d}",
        "counts": counts,
    }
    return manifest, entry


def _validated_relative_path(entry: dict[str, Any]) -> Path:
    relative = entry.get("path")
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("package file path must be a relative POSIX path")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("package file path escapes the package root")
    return candidate


def _verify_file(root: Path, entry: dict[str, Any]) -> int | None:
    candidate = _validated_relative_path(entry)
    relative = cast("str", entry["path"])
    path = root / candidate
    current = root
    for part in candidate.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"package paths must not contain symlinks: {relative}")
    if not path.is_file():
        raise ValueError(f"missing package file: {relative}")
    if path.stat().st_size != entry.get("byte_count"):
        raise ValueError(f"package byte_count mismatch: {relative}")
    if sha256_file(path) != entry.get("sha256"):
        raise ValueError(f"package checksum mismatch: {relative}")
    role = entry.get("role")
    if role == "other":
        if entry.get("row_count") is not None:
            raise ValueError(f"other package file must not declare row_count: {relative}")
        return None
    if role not in {"cases", "events", "attachments"}:
        raise ValueError(f"unsupported package file role: {role}")
    if entry.get("media_type") != "application/x-ndjson":
        raise ValueError(f"counted package file must be NDJSON: {relative}")
    rows = _read_ndjson(path, label=cast("str", role))
    if len(rows) != entry.get("row_count"):
        raise ValueError(f"package row_count mismatch: {relative}")
    if role == "events":
        _validate_event_order(rows)
    return len(rows)


def verify_archive_package(root: Path) -> dict[str, Any]:
    """Verify package identity, exact file inventory, byte digests, and row counts."""
    if root.is_symlink():
        raise ValueError("package root must not be a symlink")
    manifest_path = root / "archive-package.json"
    if manifest_path.is_symlink():
        raise ValueError("package manifest must not be a symlink")
    manifest = _load_json_object(manifest_path, label="archive package manifest")
    if manifest.get("schema_version") != PACKAGE_SCHEMA_VERSION:
        raise ValueError("unsupported archive package schema_version")
    instance_id = manifest.get("instance_id")
    archive_revision = manifest.get("archive_revision")
    if not isinstance(instance_id, str):
        raise ValueError("package instance_id must be a registered instance")
    get_instance(instance_id)
    if not isinstance(archive_revision, int) or isinstance(archive_revision, bool):
        raise ValueError("package archive_revision must be a positive integer")
    if archive_revision < 1:
        raise ValueError("package archive_revision must be a positive integer")
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise ValueError("package source must be an object")
    repository = source.get("repository")
    repository_revision = source.get("revision")
    if not isinstance(repository, str) or not isinstance(repository_revision, str):
        raise ValueError("package source repository and revision must be strings")
    _validate_repository(instance_id, repository, repository_revision)
    identifier = manifest.get("package_id")
    if not isinstance(identifier, str) or not HEX64.fullmatch(identifier):
        raise ValueError("package_id must be a lowercase SHA-256 digest")
    if package_id(manifest) != identifier:
        raise ValueError("package identity mismatch")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("package files must be a non-empty array")
    if [entry.get("order") for entry in files if isinstance(entry, dict)] != list(
        range(1, len(files) + 1)
    ):
        raise ValueError("package file order must be exactly 1..N")
    for raw_entry in files:
        if not isinstance(raw_entry, dict):
            raise ValueError("package file entry must be an object")
        _validated_relative_path(raw_entry)
    declared_paths = [cast("dict[str, Any]", entry).get("path") for entry in files]
    if len(declared_paths) != len(set(declared_paths)):
        raise ValueError("package paths must be unique")
    actual_paths: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            relative = path.relative_to(root).as_posix()
            raise ValueError(f"package paths must not contain symlinks: {relative}")
        if path.is_file() and path.name != "archive-package.json":
            actual_paths.add(path.relative_to(root).as_posix())
    if actual_paths != set(declared_paths):
        raise ValueError("package file inventory does not match manifest")
    role_counts = {"cases": 0, "events": 0, "attachments": 0}
    for raw_entry in files:
        if not isinstance(raw_entry, dict):
            raise ValueError("package file entry must be an object")
        count = _verify_file(root, raw_entry)
        role = raw_entry.get("role")
        if count is not None and role in role_counts:
            role_counts[role] += count
    counts = manifest.get("counts")
    if not isinstance(counts, dict) or counts.get("file_count") != len(files):
        raise ValueError("package file_count mismatch")
    expected = {
        "cases": counts.get("case_count"),
        "events": counts.get("event_count"),
        "attachments": counts.get("attachment_count"),
    }
    if role_counts != expected:
        raise ValueError("package role counts do not reconcile")
    events = _read_ndjson(root / "events.ndjson", label="events")
    first_sequence, last_sequence = _validate_event_order(events)
    if manifest.get("ordering") != {
        "event_key": EVENT_ORDER_KEY,
        "first_source_sequence": first_sequence,
        "last_source_sequence": last_sequence,
    }:
        raise ValueError("package event ordering bounds do not reconcile")
    takedown_path = root / "metadata" / "takedown-inventory.ndjson"
    if sha256_file(takedown_path) != manifest.get("takedown_revision"):
        raise ValueError("takedown revision does not match inventory bytes")
    metadata = _load_json_object(
        root / "metadata" / "package-metadata.json", label="package metadata"
    )
    if metadata.get("schema") != PACKAGE_METADATA_SCHEMA:
        raise ValueError("unsupported package metadata schema")
    if metadata.get("archive_revision") != manifest.get("archive_revision"):
        raise ValueError("package metadata archive revision mismatch")
    if metadata.get("takedown_revision") != manifest.get("takedown_revision"):
        raise ValueError("package metadata takedown revision mismatch")
    package_kind = metadata.get("package_kind")
    base_revision = metadata.get("base_archive_revision")
    if package_kind == "snapshot" and base_revision is not None:
        raise ValueError("snapshot package metadata must not declare a base revision")
    if package_kind == "delta" and (
        not isinstance(base_revision, int)
        or isinstance(base_revision, bool)
        or base_revision < 1
        or base_revision >= archive_revision
    ):
        raise ValueError("delta package metadata requires an earlier positive base revision")
    if package_kind not in {"snapshot", "delta"}:
        raise ValueError("unsupported package metadata kind")
    provenance = _load_json_object(root / "metadata" / "provenance.json", label="provenance")
    retention = _load_json_object(root / "metadata" / "retention.json", label="retention")
    if metadata.get("provenance") != provenance:
        raise ValueError("package provenance metadata does not reconcile")
    if metadata.get("retention") != retention:
        raise ValueError("package retention metadata does not reconcile")
    if not isinstance(retention.get("status"), str) or not retention["status"]:
        raise ValueError("retention metadata requires a non-empty status")
    expected_contracts = {
        "foi_process_archive_package": PACKAGE_SCHEMA_VERSION,
        "fyi_cli_process_event": "1.0.0",
    }
    if metadata.get("compatible_contracts") != expected_contracts:
        raise ValueError("package compatibility contracts do not reconcile")
    return {
        "verified": True,
        "package_id": identifier,
        "manifest_sha256": sha256_file(manifest_path),
        "instance_id": instance_id,
        "archive_revision": archive_revision,
        "counts": counts,
    }


def _write_indexes(output_root: Path, instance_id: str, entry: PackageIndexEntry) -> None:
    existing = _load_index(output_root, instance_id)
    revisions = [] if existing is None else list(existing["revisions"])
    matches = [row for row in revisions if row.get("archive_revision") == entry["archive_revision"]]
    if matches:
        if matches != [entry]:
            raise ValueError("archive revision already indexes a different package")
    else:
        if revisions and entry["archive_revision"] <= revisions[-1]["archive_revision"]:
            raise ValueError("archive revisions must be appended in increasing order")
        revisions.append(entry)
    index = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "instance_id": instance_id,
        "revisions": revisions,
    }
    index_bytes = canonical_json(index) + b"\n"
    index_dir = output_root / "indexes" / instance_id
    _atomic_write(index_dir / "index.json", index_bytes)
    latest = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "instance_id": instance_id,
        "index_sha256": sha256_bytes(index_bytes),
        "revision": revisions[-1],
    }
    latest_bytes = canonical_json(latest) + b"\n"
    _atomic_write(index_dir / "latest.json", latest_bytes)

    catalog_path = output_root / "catalog.json"
    catalog: dict[str, Any] = (
        _load_json_object(catalog_path, label="package catalog")
        if catalog_path.exists()
        else {"schema_version": CATALOG_SCHEMA_VERSION, "instances": []}
    )
    if catalog.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise ValueError("unsupported package catalog schema_version")
    rows = {
        row["instance_id"]: row
        for row in cast("list[dict[str, Any]]", catalog.get("instances", []))
    }
    rows[instance_id] = {
        "instance_id": instance_id,
        "index_path": f"indexes/{instance_id}/index.json",
        "latest_path": f"indexes/{instance_id}/latest.json",
        "latest_archive_revision": revisions[-1]["archive_revision"],
        "latest_package_id": revisions[-1]["package_id"],
        "index_sha256": sha256_bytes(index_bytes),
        "latest_sha256": sha256_bytes(latest_bytes),
        "revision_count": len(revisions),
    }
    catalog["instances"] = [rows[key] for key in sorted(rows)]
    _atomic_write(catalog_path, canonical_json(catalog) + b"\n")


def build_archive_package(inputs: PackageInputs, output_root: Path) -> dict[str, Any]:
    """Build or idempotently confirm one immutable package and update indexes."""
    index = _load_index(output_root, inputs.instance_id)
    _validate_inputs(inputs, index)
    package_dir = output_root / "packages" / inputs.instance_id / f"{inputs.archive_revision:020d}"
    package_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".package-", dir=package_dir.parent))
    try:
        manifest, entry = _build_staging(inputs, staging)
        verify_archive_package(staging)
        if package_dir.exists():
            existing = verify_archive_package(package_dir)
            if existing["package_id"] != manifest["package_id"]:
                raise ValueError("archive revision already contains a different immutable package")
            shutil.rmtree(staging)
        else:
            staging.replace(package_dir)
        _write_indexes(output_root, inputs.instance_id, entry)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return {
        "package_path": entry["package_path"],
        "package_id": entry["package_id"],
        "manifest_sha256": entry["manifest_sha256"],
        "instance_id": inputs.instance_id,
        "archive_revision": inputs.archive_revision,
        "counts": entry["counts"],
    }


def verify_package_store(output_root: Path) -> dict[str, Any]:
    """Verify all indexed packages, latest pointers, and compact catalogue rows."""
    catalog = _load_json_object(output_root / "catalog.json", label="package catalog")
    if catalog.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise ValueError("unsupported package catalog schema_version")
    instances = catalog.get("instances")
    if not isinstance(instances, list):
        raise ValueError("package catalog instances must be an array")
    ids = [row.get("instance_id") for row in instances if isinstance(row, dict)]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ValueError("package catalogue instances must be unique and sorted")
    package_count = 0
    for raw_row in instances:
        if not isinstance(raw_row, dict):
            raise ValueError("package catalog row must be an object")
        instance_id = cast("str", raw_row["instance_id"])
        index = _load_index(output_root, instance_id)
        if index is None:
            raise ValueError(f"missing package index for {instance_id}")
        revisions = cast("list[dict[str, Any]]", index["revisions"])
        revision_numbers = [int(entry["archive_revision"]) for entry in revisions]
        if revision_numbers != sorted(set(revision_numbers)):
            raise ValueError(f"package revisions are not strictly increasing for {instance_id}")
        latest = _load_json_object(
            output_root / "indexes" / instance_id / "latest.json", label="latest pointer"
        )
        index_path = output_root / "indexes" / instance_id / "index.json"
        latest_path = output_root / "indexes" / instance_id / "latest.json"
        if latest.get("index_sha256") != sha256_file(index_path):
            raise ValueError(f"latest index checksum mismatch for {instance_id}")
        if not revisions or latest.get("revision") != revisions[-1]:
            raise ValueError(f"latest pointer mismatch for {instance_id}")
        if raw_row.get("revision_count") != len(revisions):
            raise ValueError(f"catalog revision_count mismatch for {instance_id}")
        if raw_row.get("latest_archive_revision") != revisions[-1]["archive_revision"]:
            raise ValueError(f"catalog latest revision mismatch for {instance_id}")
        if raw_row.get("latest_package_id") != revisions[-1]["package_id"]:
            raise ValueError(f"catalog latest package mismatch for {instance_id}")
        if raw_row.get("index_sha256") != sha256_file(index_path):
            raise ValueError(f"catalog index checksum mismatch for {instance_id}")
        if raw_row.get("latest_sha256") != sha256_file(latest_path):
            raise ValueError(f"catalog latest checksum mismatch for {instance_id}")
        for entry in revisions:
            archive_revision = entry.get("archive_revision")
            if (
                not isinstance(archive_revision, int)
                or isinstance(archive_revision, bool)
                or archive_revision < 1
            ):
                raise ValueError("indexed archive_revision must be a positive integer")
            expected_package_path = f"packages/{instance_id}/{archive_revision:020d}"
            if entry.get("package_path") != expected_package_path:
                raise ValueError(f"indexed package_path must equal {expected_package_path}")
            package_root = output_root / expected_package_path
            verified = verify_archive_package(package_root)
            if verified["package_id"] != entry["package_id"]:
                raise ValueError("indexed package identity mismatch")
            if verified["manifest_sha256"] != entry["manifest_sha256"]:
                raise ValueError("indexed package manifest checksum mismatch")
            if verified["archive_revision"] != entry["archive_revision"]:
                raise ValueError("indexed package revision mismatch")
            if verified["counts"] != entry["counts"]:
                raise ValueError("indexed package counts mismatch")
            package_count += 1
    return {"verified": True, "instance_count": len(instances), "package_count": package_count}
