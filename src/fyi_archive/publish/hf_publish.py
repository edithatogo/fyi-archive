"""Hugging Face dataset publishing helpers."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path, PurePosixPath

from huggingface_hub import CommitOperationAdd, CommitOperationDelete, HfApi, snapshot_download
from huggingface_hub.errors import HfHubHTTPError

DATASET_GITIGNORE = """# Generated dataset mirror.
.cache/
__pycache__/
*.py[cod]
"""

PRESERVED_DATASET_ROOTS = {
    ".gitattributes",
    ".gitignore",
    "CITATION.cff",
    "DATASET_CARD.md",
    "LICENSE",
    "NOTICE.md",
    "README.md",
}


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
    clean_stale: bool = True,
) -> object:
    """Upload a folder to a Hugging Face dataset repository."""
    api = HfApi(token=token)
    ensure_dataset_repo(api=api, repo_id=repo_id)
    base_path = PurePosixPath(path_in_repo) if path_in_repo else PurePosixPath()
    if clean_stale and not path_in_repo:
        _prepare_dataset_repo(api=api, repo_id=repo_id, token=token)
    operations: list[CommitOperationAdd] = []
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


def ensure_dataset_repo(*, api: HfApi, repo_id: str) -> None:
    """Create the dataset repo if needed, tolerating HF rate limits for existing repos."""
    try:
        api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
    except HfHubHTTPError as exc:
        if getattr(exc.response, "status_code", None) == 429:
            return
        raise


def _prepare_dataset_repo(*, api: HfApi, repo_id: str, token: str) -> None:
    """Replace source-repo ignores and remove stale top-level files before publishing."""
    api.create_commit(
        repo_id=repo_id,
        repo_type="dataset",
        operations=[
            CommitOperationAdd(
                path_or_fileobj=DATASET_GITIGNORE.encode("utf-8"),
                path_in_repo=".gitignore",
            ),
        ],
        commit_message="Prepare fyi archive dataset mirror",
        token=token,
    )
    delete_operations = [
        CommitOperationDelete(path_in_repo=item.path, is_folder=hasattr(item, "tree_id"))
        for item in api.list_repo_tree(repo_id=repo_id, repo_type="dataset")
        if item.path not in PRESERVED_DATASET_ROOTS
    ]
    if delete_operations:
        api.create_commit(
            repo_id=repo_id,
            repo_type="dataset",
            operations=delete_operations,
            commit_message="Clean stale fyi archive dataset artifacts",
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
