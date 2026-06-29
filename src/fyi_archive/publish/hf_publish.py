"""Hugging Face dataset publishing helpers."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path, PurePosixPath

from huggingface_hub import CommitOperationAdd, HfApi, snapshot_download


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
    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
    operations: list[CommitOperationAdd] = []
    base_path = PurePosixPath(path_in_repo) if path_in_repo else PurePosixPath()
    for path in sorted(folder_path.rglob("*")):
        if not path.is_file() or ".cache" in path.parts:
            continue
        relative_path = path.relative_to(folder_path).as_posix()
        operations.append(
            CommitOperationAdd(
                path_or_fileobj=path,
                path_in_repo=(base_path / relative_path).as_posix(),
            ),
        )
    if not operations:
        return None
    return api.create_commit(
        repo_id=repo_id,
        repo_type="dataset",
        operations=operations,
        commit_message=commit_message,
        token=token,
    )


def verify_remote_manifest(
    *,
    repo_id: str,
    local_manifest: Path,
    token: str | None = None,
    revision: str | None = None,
) -> bool:
    """Download the remote manifest and compare SHA-256 with the local manifest."""
    with tempfile.TemporaryDirectory() as cache_dir:
        snapshot_path = Path(
            snapshot_download(
                repo_id=repo_id,
                repo_type="dataset",
                token=token,
                revision=revision,
                cache_dir=cache_dir,
                allow_patterns="manifests/latest_manifest.json",
                force_download=True,
            ),
        )
        remote_manifest = snapshot_path / "manifests" / "latest_manifest.json"
        local_sha = sha256_file(local_manifest)
        remote_sha = sha256_file(remote_manifest)
        return local_sha == remote_sha
