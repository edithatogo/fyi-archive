"""Verified GitHub artifact fallback for authority catalog discovery."""

from __future__ import annotations

import hashlib
import io
import json
import os
import urllib.error
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class CatalogArtifactError(RuntimeError):
    """Raised when a fallback artifact is missing, corrupt, or malformed."""


def validate_catalog_payload(payload: dict[str, Any]) -> None:
    """Fail closed unless the catalog has the expected body-list structure."""
    bodies = payload.get("bodies")
    provenance = payload.get("provenance")
    if not isinstance(bodies, list) or not all(isinstance(row, dict) for row in bodies):
        raise CatalogArtifactError("catalog artifact bodies must be a list of objects")
    if not isinstance(provenance, dict) or not provenance.get("payload_sha256"):
        raise CatalogArtifactError("catalog artifact provenance checksum is missing")


def catalog_sha256(path: Path) -> str:
    """Return the SHA-256 digest of a local catalog artifact."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_catalog_provenance(path: Path, provenance: dict[str, Any]) -> None:
    """Write provenance JSON with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _github_json(url: str, token: str) -> Any:  # noqa: ANN401
    request = urllib.request.Request(  # noqa: S310
        url,
        headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as error:
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
    runs = _github_json(
        f"{root}/repos/{repository}/actions/workflows/{workflow}/runs?status=success&per_page=20",
        token,
    )
    candidates = runs.get("workflow_runs", []) if isinstance(runs, dict) else []
    for run in candidates:
        run_id = run.get("id") if isinstance(run, dict) else None
        if not isinstance(run_id, int):
            continue
        artifacts = _github_json(f"{root}/repos/{repository}/actions/runs/{run_id}/artifacts", token)
        for artifact in artifacts.get("artifacts", []) if isinstance(artifacts, dict) else []:
            if not isinstance(artifact, dict) or not str(artifact.get("name", "")).startswith("catalog-"):
                continue
            download_url = artifact.get("archive_download_url")
            if not isinstance(download_url, str):
                continue
            request = urllib.request.Request(  # noqa: S310
                download_url,
                headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}"},
            )
            try:
                with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
                    archive = response.read()
                with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
                    names = set(bundle.namelist())
                    catalog_name = next(
                        (name for name in names if name.endswith("discovered_bodies.json")), None
                    )
                    provenance_name = next(
                        (name for name in names if name.endswith("discovered_bodies.provenance.json")), None
                    )
                    if not catalog_name or not provenance_name:
                        raise CatalogArtifactError("catalog artifact is missing required files")
                    payload = json.loads(bundle.read(catalog_name).decode("utf-8"))
                    source_provenance = json.loads(bundle.read(provenance_name).decode("utf-8"))
                if not isinstance(payload, dict) or not isinstance(source_provenance, dict):
                    raise CatalogArtifactError("catalog artifact JSON must contain objects")
                validate_catalog_payload(payload)
                expected = str(payload["provenance"]["payload_sha256"])
                if expected != str(source_provenance.get("payload_sha256")):
                    raise CatalogArtifactError("catalog artifact provenance checksum mismatch")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = output_path.with_suffix(output_path.suffix + ".tmp")
                temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
                temporary.replace(output_path)
                fallback = {
                    "mode": "fallback",
                    "failed_live_source_url": failed_live_source_url or source_provenance.get("catalog_url"),
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
            except (OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError) as error:
                raise CatalogArtifactError(f"catalog artifact validation failed: {error}") from error
    raise CatalogArtifactError("no successful verified catalog artifact found")
