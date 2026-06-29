"""Versioned mirror verification evidence helpers."""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from huggingface_hub import snapshot_download

from fyi_archive.publish.hf_publish import sha256_file
from fyi_archive.publish.osf_publish import list_files as list_osf_files
from fyi_archive.publish.verification import (
    MirrorVerification,
    RemoteArtifact,
    build_local_artifacts,
    compare_artifacts,
    manifest_record_count,
    mirror_verified,
)
from fyi_archive.publish.zenodo_publish import deposition_artifacts, get_deposition
from fyi_archive.version import __version__

DEFAULT_PUBLICATION_ARTIFACTS = (
    Path("manifests/latest_manifest.json"),
    Path("manifests/latest_manifest.parquet"),
    Path("manifests/authorities.json"),
    Path("metadata/croissant.jsonld"),
    Path("metadata/frictionless.json"),
    Path("metadata/schema.org.jsonld"),
    Path("dist/fyi_archive.duckdb"),
    Path("dist/sbom.cdx.json"),
    Path("dist/provenance.json"),
)


def utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(UTC)


def archive_publication_version(
    *, generated_at: datetime, package_version: str = __version__
) -> str:
    """Build a monthly archive publication version distinct from package SemVer."""
    return f"{package_version}+archive.{generated_at:%Y.%m}"


def existing_artifact_paths(
    *,
    root: Path = Path(),
    artifact_paths: list[Path] | None = None,
) -> list[Path]:
    """Return existing local publication artifacts resolved under root."""
    candidates = artifact_paths or list(DEFAULT_PUBLICATION_ARTIFACTS)
    existing = []
    for path in candidates:
        resolved = path if path.is_absolute() else root / path
        if resolved.exists():
            existing.append(resolved)
    return existing


def verify_huggingface_dataset(
    *,
    repo_id: str,
    token: str | None,
    local_artifacts: list[Path],
    manifest_path: Path,
    repo_root: Path = Path(),
    revision: str | None = None,
) -> MirrorVerification:
    """Verify local artifacts against a Hugging Face dataset snapshot."""
    repo_paths = [repo_relative_path(artifact, repo_root) for artifact in local_artifacts]
    allow_patterns = [path.as_posix() for path in repo_paths]
    with tempfile.TemporaryDirectory() as cache_dir:
        snapshot_path = Path(
            snapshot_download(
                repo_id=repo_id,
                repo_type="dataset",
                token=token,
                revision=revision,
                allow_patterns=allow_patterns,
                cache_dir=cache_dir,
                force_download=True,
            ),
        )
        remote_artifacts = []
        for artifact, repo_path in zip(local_artifacts, repo_paths, strict=True):
            remote_path = snapshot_path / repo_path.as_posix()
            if not remote_path.exists():
                continue
            remote_artifacts.append(
                RemoteArtifact(
                    name=artifact.name,
                    size=remote_path.stat().st_size,
                    checksum=f"sha256:{sha256_file(remote_path)}",
                    url=f"https://huggingface.co/datasets/{repo_id}/resolve/main/{repo_path.as_posix()}",
                ),
            )
    artifact_results = compare_artifacts(
        local_artifacts=build_local_artifacts(local_artifacts),
        remote_artifacts=remote_artifacts,
    )
    return MirrorVerification(
        mirror="huggingface",
        verified=mirror_verified(artifact_results),
        record_count=manifest_record_count(manifest_path),
        artifacts=artifact_results,
        details={"repo_id": repo_id, "revision": revision},
    )


def repo_relative_path(path: Path, repo_root: Path) -> Path:
    """Return a repository-relative path for mirror APIs."""
    if not path.is_absolute():
        return path
    try:
        return path.relative_to(repo_root.resolve())
    except ValueError:
        return Path(path.name)


def verify_zenodo_deposition(
    *,
    token: str,
    deposition_id: int,
    local_artifacts: list[Path],
    manifest_path: Path,
    api_url: str,
) -> MirrorVerification:
    """Verify local artifacts against a Zenodo deposition."""
    deposition = get_deposition(token=token, deposition_id=deposition_id, api_url=api_url)
    artifact_results = compare_artifacts(
        local_artifacts=build_local_artifacts(local_artifacts),
        remote_artifacts=deposition_artifacts(deposition),
    )
    return MirrorVerification(
        mirror="zenodo",
        verified=mirror_verified(artifact_results),
        record_count=manifest_record_count(manifest_path),
        artifacts=artifact_results,
        details={
            "deposition_id": deposition_id,
            "doi": deposition.get("doi"),
            "api_url": api_url,
        },
    )


def verify_osf_node(
    *,
    token: str,
    node_id: str,
    local_artifacts: list[Path],
    manifest_path: Path,
    api_url: str,
) -> MirrorVerification:
    """Verify local artifacts against an OSF Storage node."""
    artifact_results = compare_artifacts(
        local_artifacts=build_local_artifacts(local_artifacts),
        remote_artifacts=list_osf_files(token=token, node_id=node_id, api_url=api_url),
    )
    return MirrorVerification(
        mirror="osf",
        verified=mirror_verified(artifact_results),
        record_count=manifest_record_count(manifest_path),
        artifacts=artifact_results,
        details={"node_id": node_id, "api_url": api_url},
    )


def verification_bundle(
    *,
    reports: list[MirrorVerification],
    manifest_path: Path,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a versioned verification payload for repository storage."""
    timestamp = generated_at or utc_now()
    return {
        "generated_at": timestamp.isoformat(),
        "archive_publication_version": archive_publication_version(generated_at=timestamp),
        "package_version": __version__,
        "publication_month": timestamp.strftime("%Y-%m"),
        "manifest": {
            "path": manifest_path.as_posix(),
            "sha256": sha256_file(manifest_path),
            "record_count": manifest_record_count(manifest_path),
        },
        "mirrors": [asdict(report) for report in reports],
        "verified": all(report.verified for report in reports),
    }


def write_versioned_verification_bundle(
    *,
    reports: list[MirrorVerification],
    manifest_path: Path,
    output_dir: Path = Path("versions"),
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Write monthly and latest mirror verification evidence in the repository."""
    bundle = verification_bundle(
        reports=reports,
        manifest_path=manifest_path,
        generated_at=generated_at,
    )
    publication_month = str(bundle["publication_month"])
    month_dir = output_dir / publication_month
    month_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(bundle, indent=2, sort_keys=True) + "\n"
    (month_dir / "mirror_verification.json").write_text(payload, encoding="utf-8")
    (output_dir / "latest_mirror_verification.json").write_text(payload, encoding="utf-8")
    return bundle
