import json
from pathlib import Path

import pytest

from scripts.build_historical_archive_manifest import build_manifest


def test_manifest_hashes_declared_artifacts(tmp_path: Path) -> None:
    artifact = tmp_path / "au.json"
    artifact.write_bytes(b"{}\n")
    import hashlib

    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (tmp_path / "au.status.json").write_text(
        json.dumps({
            "artifacts": {"au.json": {"byte_count": artifact.stat().st_size, "sha256": digest}},
            "replay_limit_per_instance": 25,
            "replay_delay_seconds": 3,
            "replay_timeout_seconds": 15,
        }),
        encoding="utf-8",
    )
    manifest = build_manifest(tmp_path, instance_id="au")
    assert manifest["schema"] == "fyi-archive.immutable-historical-manifest.v1"
    assert len(manifest["manifest_sha256"]) == 64


def test_manifest_rejects_changed_artifact(tmp_path: Path) -> None:
    (tmp_path / "au.json").write_text("changed\n", encoding="utf-8")
    (tmp_path / "au.status.json").write_text(
        json.dumps({"artifacts": {"au.json": {"byte_count": 3, "sha256": "0" * 64}}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        build_manifest(tmp_path, instance_id="au")
