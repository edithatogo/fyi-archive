"""Build a hash-pinned manifest for one bounded historical archive batch."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(root: Path, *, instance_id: str) -> dict[str, Any]:
    status_path = root / f"{instance_id}.status.json"
    if not status_path.is_file():
        raise ValueError(f"missing status artifact: {status_path}")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    artifacts = status.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError("status artifact has no hashed artifacts")
    files = []
    for name, metadata in sorted(artifacts.items()):
        path = root / name
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
        "status_artifact": status_path.name,
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_manifest(args.root, instance_id=args.instance_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
