#!/usr/bin/env python3
"""Generate release provenance for archive artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_ARTIFACT_GLOBS = (
    "dist/*.wacz",
    "dist/*.warc",
    "dist/*.warc.gz",
    "dist/*.duckdb",
    "dist/*.json",
    "dist/*.parquet",
    "manifests/latest_manifest.json",
    "manifests/latest_changes.json",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate dist/provenance.json.")
    parser.add_argument("--output", default="dist/provenance.json", help="Output JSON path.")
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Artifact file or glob to hash. Can be repeated.",
    )
    parser.add_argument("--fetch-start", default=os.environ.get("FYI_FETCH_WINDOW_START"))
    parser.add_argument("--fetch-end", default=os.environ.get("FYI_FETCH_WINDOW_END"))
    parser.add_argument("--fetch-label", default=os.environ.get("FYI_FETCH_WINDOW_LABEL"))
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(args: Sequence[str]) -> str | None:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def git_metadata() -> dict[str, str | bool | None]:
    status = git_output(["status", "--porcelain"])
    return {
        "commit": git_output(["rev-parse", "HEAD"]),
        "branch": git_output(["rev-parse", "--abbrev-ref", "HEAD"]),
        "dirty": bool(status),
    }


def expand_artifact_patterns(patterns: Iterable[str], output_path: Path) -> list[Path]:
    artifacts: set[Path] = set()
    for pattern in patterns:
        path = Path(pattern)
        matches = list(Path().glob(pattern)) if any(char in pattern for char in "*?[]") else [path]
        for match in matches:
            if match.is_file() and match.resolve() != output_path.resolve():
                artifacts.add(match)
    return sorted(artifacts)


def artifact_records(paths: Iterable[Path]) -> list[dict[str, str | int]]:
    records = []
    for path in paths:
        records.append(
            {
                "path": path.as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            },
        )
    return records


def build_provenance(
    *,
    artifact_patterns: Sequence[str],
    output_path: Path,
    fetch_start: str | None,
    fetch_end: str | None,
    fetch_label: str | None,
) -> dict[str, object]:
    lockfile = Path("uv.lock")
    patterns = artifact_patterns or list(DEFAULT_ARTIFACT_GLOBS)
    artifacts = expand_artifact_patterns(patterns, output_path)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": git_metadata(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "runner": os.environ.get("GITHUB_RUN_ID"),
            "workflow": os.environ.get("GITHUB_WORKFLOW"),
        },
        "fetch_window": {
            "start": fetch_start,
            "end": fetch_end,
            "label": fetch_label,
        },
        "lockfile": {
            "path": lockfile.as_posix(),
            "sha256": sha256_file(lockfile) if lockfile.exists() else None,
        },
        "artifacts": artifact_records(artifacts),
    }


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    provenance = build_provenance(
        artifact_patterns=args.artifact,
        output_path=output_path,
        fetch_start=args.fetch_start,
        fetch_end=args.fetch_end,
        fetch_label=args.fetch_label,
    )
    output_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(f"Provenance written to {output_path}")


if __name__ == "__main__":
    main()
