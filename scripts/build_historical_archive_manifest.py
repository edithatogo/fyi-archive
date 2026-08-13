"""Build a hash-pinned manifest for one bounded historical archive batch."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, cast

INSTANCE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def declared_artifact_path(root: Path, value: object) -> tuple[str, Path]:
    if not isinstance(value, str) or not value:
        raise ValueError("artifact path must be a relative POSIX path")
    if "\\" in value or ":" in value or value.startswith("./") or "/./" in value:
        raise ValueError("artifact path must be a relative POSIX path")
    relative = PurePosixPath(value)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError("artifact path escapes the manifest root")
    candidate = root.joinpath(*relative.parts)
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"artifact path must not contain symlinks: {value}")
    return value, candidate


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(
    root: Path,
    *,
    instance_id: str,
    status_path: Path | None = None,
) -> dict[str, Any]:
    if not INSTANCE_ID.fullmatch(instance_id):
        raise ValueError("instance_id must be a lowercase slug")
    if root.is_symlink():
        raise ValueError("manifest root must not be a symlink")
    status_path = status_path or root / f"{instance_id}.status.json"
    try:
        status_relative = status_path.relative_to(root).as_posix()
    except ValueError as error:
        raise ValueError("status artifact must be below the manifest root") from error
    _, validated_status_path = declared_artifact_path(root, status_relative)
    if validated_status_path != status_path or not status_path.is_file():
        raise ValueError(f"missing status artifact: {status_path}")
    status = cast("dict[str, Any]", json.loads(status_path.read_text(encoding="utf-8")))
    if not isinstance(status, dict):
        raise ValueError("status artifact must contain an object")
    artifacts = status.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError("status artifact has no hashed artifacts")
    declared = cast("dict[str, Any]", artifacts)
    files: list[dict[str, Any]] = []
    for raw_name, raw_metadata in sorted(declared.items()):
        name, path = declared_artifact_path(root, raw_name)
        if not isinstance(raw_metadata, dict):
            raise ValueError(f"artifact metadata must contain an object: {name}")
        metadata = cast("dict[str, Any]", raw_metadata)
        if not path.is_file():
            raise ValueError(f"missing declared artifact: {path}")
        actual = {"byte_count": path.stat().st_size, "sha256": sha256(path)}
        if actual != metadata:
            raise ValueError(f"artifact hash mismatch: {name}")
        files.append({"name": name, **actual})
    payload: dict[str, Any] = {
        "schema": "fyi-archive.immutable-historical-manifest.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "instance_id": instance_id,
        "source": "internet_archive_cdx_and_replay",
        "status_artifact": status_relative,
        "replay_limit_per_instance": status["replay_limit_per_instance"],
        "replay_delay_seconds": status["replay_delay_seconds"],
        "replay_timeout_seconds": status["replay_timeout_seconds"],
        "artifacts": files,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["manifest_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--status", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_manifest(args.root, instance_id=args.instance_id, status_path=args.status)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
