"""Verified GitHub artifact fallback for authority catalog discovery."""

from __future__ import annotations

import hashlib
import io
import json
import os
import urllib.error
import urllib.request
import zipfile
import zlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast


class CatalogArtifactError(RuntimeError):
    """Raised when a fallback artifact is missing, corrupt, or malformed."""


MAX_GITHUB_JSON_BYTES = 4 * 1024 * 1024
MAX_CATALOG_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_CATALOG_ARCHIVE_ENTRIES = 32
MAX_CATALOG_MEMBER_BYTES = 8 * 1024 * 1024
MAX_CATALOG_UNCOMPRESSED_BYTES = 16 * 1024 * 1024


class ReadableResponse(Protocol):
    """Minimal response interface needed for bounded reads."""

    def read(self, amount: int = -1) -> bytes:
        """Read at most ``amount`` bytes."""
        ...


def _read_bounded(response: ReadableResponse, *, limit: int, label: str) -> bytes:
    """Read at most ``limit`` bytes and reject truncated oversized responses."""
    content = response.read(limit + 1)
    if len(content) > limit:
        raise CatalogArtifactError(f"{label} exceeds the {limit}-byte limit")
    return content


def _required_member(bundle: zipfile.ZipFile, suffix: str) -> zipfile.ZipInfo:
    matches = [
        item for item in bundle.infolist() if not item.is_dir() and item.filename.endswith(suffix)
    ]
    if not matches:
        raise CatalogArtifactError(f"catalog artifact is missing required file: {suffix}")
    if len(matches) != 1:
        raise CatalogArtifactError(f"catalog artifact must contain exactly one {suffix}")
    return matches[0]


def _read_member(bundle: zipfile.ZipFile, member: zipfile.ZipInfo, *, label: str) -> bytes:
    with bundle.open(member) as stream:
        content = _read_bounded(stream, limit=MAX_CATALOG_MEMBER_BYTES, label=label)
    if len(content) != member.file_size:
        raise CatalogArtifactError(f"{label} size does not match its ZIP metadata")
    return content


def parse_catalog_archive(archive: bytes) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse a bounded GitHub artifact without extracting attacker-controlled paths."""
    if len(archive) > MAX_CATALOG_ARCHIVE_BYTES:
        raise CatalogArtifactError("catalog archive exceeds the compressed size limit")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            members = bundle.infolist()
            if len(members) > MAX_CATALOG_ARCHIVE_ENTRIES:
                raise CatalogArtifactError("catalog archive contains too many entries")
            names = [item.filename for item in members]
            if len(names) != len(set(names)):
                raise CatalogArtifactError("catalog archive contains duplicate member names")
            if any(item.file_size > MAX_CATALOG_MEMBER_BYTES for item in members):
                raise CatalogArtifactError("catalog archive member exceeds the size limit")
            if sum(item.file_size for item in members) > MAX_CATALOG_UNCOMPRESSED_BYTES:
                raise CatalogArtifactError("catalog archive exceeds the uncompressed size limit")
            catalog_info = _required_member(bundle, "discovered_bodies.json")
            provenance_info = _required_member(bundle, "discovered_bodies.provenance.json")
            raw_payload: object = json.loads(
                _read_member(bundle, catalog_info, label="catalog payload").decode("utf-8")
            )
            raw_provenance: object = json.loads(
                _read_member(bundle, provenance_info, label="catalog provenance").decode("utf-8")
            )
    except (
        OSError,
        ValueError,
        UnicodeDecodeError,
        zipfile.BadZipFile,
        EOFError,
        KeyError,
        NotImplementedError,
        RuntimeError,
        zlib.error,
        json.JSONDecodeError,
    ) as error:
        raise CatalogArtifactError(f"catalog artifact validation failed: {error}") from error
    if not isinstance(raw_payload, dict) or not isinstance(raw_provenance, dict):
        raise CatalogArtifactError("catalog artifact JSON must contain objects")
    payload = cast("dict[str, Any]", raw_payload)
    provenance = cast("dict[str, Any]", raw_provenance)
    validate_catalog_payload(payload)
    return payload, provenance


def validate_catalog_payload(payload: dict[str, Any]) -> None:
    """Fail closed unless the catalog has the expected body-list structure."""
    bodies = payload.get("bodies")
    provenance = payload.get("provenance")
    if not isinstance(bodies, list) or not all(
        isinstance(row, dict) for row in cast("list[object]", bodies)
    ):
        raise CatalogArtifactError("catalog artifact bodies must be a list of objects")
    if not isinstance(provenance, dict):
        raise CatalogArtifactError("catalog artifact provenance checksum is missing")
    typed_provenance = cast("dict[str, Any]", provenance)
    if not typed_provenance.get("payload_sha256"):
        raise CatalogArtifactError("catalog artifact provenance checksum is missing")


def catalog_sha256(path: Path) -> str:
    """Return the SHA-256 digest of a local catalog artifact."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_catalog_provenance(path: Path, provenance: dict[str, Any]) -> None:
    """Write provenance JSON with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _github_json(url: str, token: str) -> object:
    request = urllib.request.Request(  # noqa: S310
        url,
        headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
            content = _read_bounded(
                response, limit=MAX_GITHUB_JSON_BYTES, label="GitHub API response"
            )
            return cast("object", json.loads(content.decode("utf-8")))
    except (urllib.error.URLError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CatalogArtifactError(f"GitHub catalog lookup failed: {error}") from error


def restore_latest_verified_catalog(
    *,
    output_path: Path,
    provenance_path: Path,
    repository: str,
    workflow: str,
    token: str | None = None,
    api_base_url: str = "https://api.github.com",
    failed_live_source_url: str | None = None,
    failure_class: str = "live_discovery_failed",
    diagnostic: str = "live catalog discovery failed; restored verified artifact",
) -> dict[str, Any]:
    """Restore the newest successful same-workflow catalog artifact atomically."""
    token = token or os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise CatalogArtifactError("GITHUB_TOKEN is required for catalog fallback")
    root = api_base_url.rstrip("/")
    raw_runs = _github_json(
        f"{root}/repos/{repository}/actions/workflows/{workflow}/runs?status=success&per_page=20",
        token,
    )
    runs = cast("dict[str, Any]", raw_runs) if isinstance(raw_runs, dict) else {}
    raw_candidates = runs.get("workflow_runs", [])
    candidates = cast("list[object]", raw_candidates) if isinstance(raw_candidates, list) else []
    for run in candidates:
        run = cast("dict[str, Any]", run) if isinstance(run, dict) else {}
        run_id = run.get("id")
        if not isinstance(run_id, int):
            continue
        raw_artifacts = _github_json(
            f"{root}/repos/{repository}/actions/runs/{run_id}/artifacts", token
        )
        artifacts = cast("dict[str, Any]", raw_artifacts) if isinstance(raw_artifacts, dict) else {}
        raw_rows = artifacts.get("artifacts", [])
        rows = cast("list[object]", raw_rows) if isinstance(raw_rows, list) else []
        for artifact in rows:
            if not isinstance(artifact, dict):
                continue
            artifact = cast("dict[str, Any]", artifact)
            if not str(artifact.get("name", "")).startswith("catalog-"):
                continue
            download_url = artifact.get("archive_download_url")
            if not isinstance(download_url, str):
                continue
            request = urllib.request.Request(  # noqa: S310
                download_url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
                    archive = _read_bounded(
                        response,
                        limit=MAX_CATALOG_ARCHIVE_BYTES,
                        label="catalog archive",
                    )
                payload, source_provenance = parse_catalog_archive(archive)
                expected = str(payload["provenance"]["payload_sha256"])
                if expected != str(source_provenance.get("payload_sha256")):
                    raise CatalogArtifactError("catalog artifact provenance checksum mismatch")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = output_path.with_suffix(output_path.suffix + ".tmp")
                temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
                temporary.replace(output_path)
                fallback: dict[str, Any] = {
                    "mode": "fallback",
                    "failed_live_source_url": failed_live_source_url
                    or source_provenance.get("catalog_url"),
                    "failure_class": failure_class,
                    "diagnostic": diagnostic[:4000],
                    "source_workflow": workflow,
                    "source_run_id": run_id,
                    "source_artifact_id": artifact.get("id"),
                    "catalog_sha256": expected,
                    "retrieved_at": datetime.now(UTC).isoformat(),
                }
                write_catalog_provenance(provenance_path, fallback)
                return fallback  # noqa: TRY300
            except (OSError, CatalogArtifactError) as error:
                raise CatalogArtifactError(
                    f"catalog artifact validation failed: {error}"
                ) from error
    raise CatalogArtifactError("no successful verified catalog artifact found")
