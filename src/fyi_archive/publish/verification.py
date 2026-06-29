"""Mirror publication verification evidence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from fyi_archive.publish.hf_publish import sha256_file


@dataclass(frozen=True)
class LocalArtifact:
    """Local artifact expected to be present on a mirror."""

    path: str
    name: str
    size: int
    sha256: str


@dataclass(frozen=True)
class RemoteArtifact:
    """Normalized remote artifact evidence."""

    name: str
    size: int | None = None
    checksum: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class ArtifactVerification:
    """Comparison result for one artifact."""

    name: str
    present: bool
    size_matches: bool | None
    checksum_matches: bool | None
    local_sha256: str
    remote_checksum: str | None = None
    remote_url: str | None = None


@dataclass(frozen=True)
class MirrorVerification:
    """Verification result for one mirror."""

    mirror: str
    verified: bool
    record_count: int
    artifacts: list[ArtifactVerification] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


def build_local_artifacts(paths: list[Path]) -> list[LocalArtifact]:
    """Build local artifact evidence for existing paths."""
    artifacts = []
    for path in paths:
        if not path.exists():
            continue
        artifacts.append(
            LocalArtifact(
                path=path.as_posix(),
                name=path.name,
                size=path.stat().st_size,
                sha256=sha256_file(path),
            ),
        )
    return artifacts


def manifest_record_count(manifest_path: Path) -> int:
    """Read manifest record count."""
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return int(data.get("meta", {}).get("record_count") or data.get("record_count") or 0)


def compare_artifacts(
    *,
    local_artifacts: list[LocalArtifact],
    remote_artifacts: list[RemoteArtifact],
) -> list[ArtifactVerification]:
    """Compare local artifacts with normalized remote evidence."""
    by_name = {artifact.name: artifact for artifact in remote_artifacts}
    results = []
    for local in local_artifacts:
        remote = by_name.get(local.name)
        if remote is None:
            results.append(
                ArtifactVerification(
                    name=local.name,
                    present=False,
                    size_matches=False,
                    checksum_matches=False,
                    local_sha256=local.sha256,
                ),
            )
            continue

        checksum_matches = checksum_matches_local(remote.checksum, local.sha256)
        results.append(
            ArtifactVerification(
                name=local.name,
                present=True,
                size_matches=None if remote.size is None else remote.size == local.size,
                checksum_matches=checksum_matches,
                local_sha256=local.sha256,
                remote_checksum=remote.checksum,
                remote_url=remote.url,
            ),
        )
    return results


def checksum_matches_local(remote_checksum: str | None, local_sha256: str) -> bool | None:
    """Return checksum comparison when remote checksum is SHA-256, otherwise unknown."""
    if remote_checksum is None:
        return None
    normalized = remote_checksum.removeprefix("sha256:").lower()
    if len(normalized) != 64:
        return None
    return normalized == local_sha256


def mirror_verified(results: list[ArtifactVerification]) -> bool:
    """Return true when all required artifacts are present and no known checks fail."""
    return all(
        result.present and result.size_matches is not False and result.checksum_matches is not False
        for result in results
    )


def write_verification_report(path: Path, reports: list[MirrorVerification]) -> None:
    """Write a JSON mirror verification report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([asdict(report) for report in reports], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def append_verification_report(path: Path, report: MirrorVerification) -> None:
    """Append or replace one mirror report in a JSON verification report."""
    existing: list[dict[str, Any]] = []
    if path.exists():
        existing_data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(existing_data, list):
            existing = [item for item in existing_data if item.get("mirror") != report.mirror]
    existing.append(asdict(report))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
