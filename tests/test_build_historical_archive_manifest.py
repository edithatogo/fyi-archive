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


@pytest.mark.parametrize(
    "name",
    ["../outside.json", "/outside.json", "nested\\file.json", "C:/outside.json", "./file.json"],
)
def test_manifest_rejects_unsafe_declared_paths(tmp_path: Path, name: str) -> None:
    (tmp_path / "au.status.json").write_text(
        json.dumps({"artifacts": {name: {"byte_count": 0, "sha256": "0" * 64}}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="artifact path"):
        build_manifest(tmp_path, instance_id="au")


def test_manifest_rejects_unsafe_instance_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="instance_id"):
        build_manifest(tmp_path, instance_id="../au")


def test_manifest_hashes_artifacts_across_safe_subdirectories(tmp_path: Path) -> None:
    import hashlib

    cdx = tmp_path / "cdx" / "au.json"
    core = tmp_path / "core" / "au.json"
    cdx.parent.mkdir()
    core.parent.mkdir()
    cdx.write_bytes(b"cdx\n")
    core.write_bytes(b"core\n")
    status_path = tmp_path / "core" / "au.status.json"
    status_path.write_text(
        json.dumps({
            "artifacts": {
                path.relative_to(tmp_path).as_posix(): {
                    "byte_count": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for path in (cdx, core)
            },
            "replay_limit_per_instance": 25,
            "replay_delay_seconds": 3,
            "replay_timeout_seconds": 15,
        }),
        encoding="utf-8",
    )

    manifest = build_manifest(tmp_path, instance_id="au", status_path=status_path)
    assert manifest["status_artifact"] == "core/au.status.json"
    assert [item["name"] for item in manifest["artifacts"]] == ["cdx/au.json", "core/au.json"]
