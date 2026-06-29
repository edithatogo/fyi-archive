"""Hugging Face dataset publishing helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def publish_folder_to_hf(
    *,
    folder_path: Path,
    repo_id: str,
    token: str,
    path_in_repo: str = "",
    commit_message: str = "Publish fyi archive dataset",
) -> object:
    """Upload a folder to a Hugging Face dataset repository."""
    del commit_message
    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
    if path_in_repo:
        msg = (
            "upload_large_folder publishes from the local folder root; path_in_repo is unsupported"
        )
        raise ValueError(msg)
    return api.upload_large_folder(
        folder_path=folder_path,
        repo_id=repo_id,
        repo_type="dataset",
        print_report=False,
    )


def verify_remote_manifest(
    *,
    repo_id: str,
    local_manifest: Path,
    token: str | None = None,
    revision: str | None = None,
) -> bool:
    """Download the remote manifest and compare SHA-256 with the local manifest."""
    snapshot_path = Path(
        snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            token=token,
            revision=revision,
            allow_patterns="manifests/latest_manifest.json",
        ),
    )
    remote_manifest = snapshot_path / "manifests" / "latest_manifest.json"
    return sha256_file(local_manifest) == sha256_file(remote_manifest)
