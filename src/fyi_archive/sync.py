"""Prospective sync orchestration helpers."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from huggingface_hub import snapshot_download

from fyi_archive.instances import DEFAULT_INSTANCE_ID, get_instance
from fyi_archive.manifest import assemble_manifest
from fyi_archive.publish.hf_publish import publish_folder_to_hf, sha256_file, verify_remote_manifest
from fyi_archive.version import __version__


@dataclass(frozen=True)
class SyncState:
    """High-water state for prospective sync."""

    last_successful_sync: str | None = None
    last_manifest_sha256: str | None = None
    record_count: int = 0


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(UTC).isoformat()


def load_sync_state(path: Path) -> SyncState:
    """Read sync high-water state, returning an empty state when missing."""
    if not path.exists():
        return SyncState()
    data = json.loads(path.read_text(encoding="utf-8"))
    return SyncState(
        last_successful_sync=data.get("last_successful_sync"),
        last_manifest_sha256=data.get("last_manifest_sha256"),
        record_count=int(data.get("record_count") or 0),
    )


def write_sync_state(path: Path, state: SyncState) -> None:
    """Write sync high-water state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "last_successful_sync": state.last_successful_sync,
                "last_manifest_sha256": state.last_manifest_sha256,
                "record_count": state.record_count,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def empty_changes(since: str | None) -> dict[str, Any]:
    """Build an empty changes document."""
    return {
        "meta": {
            "generated_at": utc_now(),
            "since": since,
            "version": __version__,
        },
        "added": [],
        "updated": [],
        "removed": [],
    }


def load_changes(path: Path, since: str | None) -> dict[str, Any]:
    """Load a changes document or return an empty one when absent."""
    if not path.exists():
        return empty_changes(since)
    changes = json.loads(path.read_text(encoding="utf-8"))
    validate_changes(changes)
    return changes


def validate_changes(changes: dict[str, Any]) -> None:
    """Validate the subset required by schemas/changes.schema.json."""
    meta = changes.get("meta")
    if not isinstance(meta, dict):
        msg = "Changes must contain object 'meta'"
        raise ValueError(msg)
    for key in ("generated_at", "version"):
        if not isinstance(meta.get(key), str):
            msg = f"Changes meta.{key} must be a string"
            raise ValueError(msg)
    if meta.get("since") is not None and not isinstance(meta.get("since"), str):
        msg = "Changes meta.since must be a string or null"
        raise ValueError(msg)

    for bucket in ("added", "updated", "removed"):
        entries = changes.get(bucket)
        if not isinstance(entries, list):
            msg = f"Changes {bucket} must be an array"
            raise ValueError(msg)
        for entry in entries:
            validate_change_entry(entry)


def validate_change_entry(entry: object) -> None:
    """Validate one content-addressed change entry."""
    if not isinstance(entry, dict):
        msg = "Change entry must be an object"
        raise ValueError(msg)
    request_id = entry.get("request_id")
    if not isinstance(request_id, int) or request_id < 1:
        msg = "Change entry request_id must be a positive integer"
        raise ValueError(msg)
    digest = entry.get("content_sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or not set(digest) <= set("0123456789abcdef")
    ):
        msg = "Change entry content_sha256 must be a 64-character lowercase hex string"
        raise ValueError(msg)
    previous = entry.get("previous_sha256")
    if previous is not None and (
        not isinstance(previous, str)
        or len(previous) != 64
        or not set(previous) <= set("0123456789abcdef")
    ):
        msg = "Change entry previous_sha256 must be null or a 64-character lowercase hex string"
        raise ValueError(msg)


def write_changes(path: Path, changes: dict[str, Any]) -> None:
    """Write latest changes JSON."""
    validate_changes(changes)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(changes, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_sync_health(path: Path, summary: dict[str, Any]) -> None:
    """Write a lightweight sync health payload."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"timestamp": utc_now(), "sync": summary}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def dry_run_materialize_changes(changes: dict[str, Any], derived_dir: Path) -> int:
    """Materialize deterministic derived records for added/updated dry-run changes."""
    derived_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for bucket in ("added", "updated"):
        for entry in changes[bucket]:
            request_id = int(entry["request_id"])
            record = {
                "request_id": request_id,
                "url_title": entry.get("url_title") or f"request-{request_id}",
                "title": f"Dry-run sync request {request_id}",
                "authority": "",
                "state": bucket,
                "html_captured": False,
                "attachments": [],
                "warc_record_ids": [],
                "content_sha256": entry["content_sha256"],
                "first_seen": None,
                "last_updated": changes["meta"]["generated_at"],
            }
            (derived_dir / f"{request_id}.json").write_text(
                json.dumps(record, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            written += 1
    return written


def run_fyi_cli_diff(
    *,
    since: str | None,
    derived_dir: Path,
    previous_manifest: Path,
    output_path: Path,
    extra_args: Sequence[str] = (),
) -> None:
    """Delegate prospective diff generation to fyi-cli."""
    command = [
        "fyi",
        "diff",
        "--derived-dir",
        str(derived_dir),
        "--previous-manifest",
        str(previous_manifest),
        "--output",
        str(output_path),
    ]
    if since is not None:
        command.extend(["--since", since])
    command.extend(extra_args)
    subprocess.run(command, check=True)


def fyi_diff_content_sha256(data: dict[str, Any]) -> str:
    """Return the raw request hash used by fyi-cli archive diffs."""
    if data.get("content_sha256"):
        return str(data["content_sha256"])
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_diff_baseline_manifest(*, derived_dir: Path, output_path: Path) -> Path:
    """Write a previous-manifest view whose hashes match fyi-cli diff semantics."""
    records = []
    for path in sorted(derived_dir.glob("*/*/request.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        request_id = int(data["id"] if "id" in data else data["request_id"])
        records.append(
            {
                "request_id": request_id,
                "url_title": str(data.get("url_title") or f"request-{request_id}"),
                "content_sha256": fyi_diff_content_sha256(data),
            },
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"requests": records}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def restore_hf_dataset(
    *,
    repo_id: str,
    token: str | None,
    manifest_dir: Path,
    derived_dir: Path,
) -> None:
    """Restore the manifest and raw request store from the Hugging Face dataset."""
    with tempfile.TemporaryDirectory() as cache_dir:
        snapshot_path = Path(
            snapshot_download(
                repo_id=repo_id,
                repo_type="dataset",
                token=token,
                allow_patterns=["manifests/*", "data/raw/requests/**"],
                cache_dir=cache_dir,
                force_download=True,
            ),
        )
        restored_manifest_dir = snapshot_path / "manifests"
        if restored_manifest_dir.exists():
            manifest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(restored_manifest_dir, manifest_dir, dirs_exist_ok=True)
        restored_requests = snapshot_path / "data" / "raw" / "requests"
        if restored_requests.exists():
            derived_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(restored_requests, derived_dir, dirs_exist_ok=True)


def changes_have_records(changes: dict[str, Any]) -> bool:
    """Return true when a changes document contains any changed request rows."""
    return any(changes[bucket] for bucket in ("added", "updated", "removed"))


def publish_sync_to_hf(
    *,
    repo_id: str,
    token: str,
    manifest_dir: Path,
    derived_dir: Path,
) -> object:
    """Publish changed sync artifacts without cleaning existing dataset exports."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        publish_root = Path(tmp_dir) / "huggingface"
        if manifest_dir.exists():
            shutil.copytree(manifest_dir, publish_root / "manifests", dirs_exist_ok=True)
        if derived_dir.exists():
            shutil.copytree(
                derived_dir,
                publish_root / "data" / "raw" / "requests",
                dirs_exist_ok=True,
            )
        return publish_folder_to_hf(
            folder_path=publish_root,
            repo_id=repo_id,
            token=token,
            commit_message="Sync fyi archive dataset",
            clean_stale=False,
        )


def run_sync(
    *,
    state_path: Path,
    derived_dir: Path,
    manifest_path: Path,
    parquet_path: Path,
    authorities_path: Path,
    changes_path: Path,
    fyi_cli_version: str,
    dry_run: bool,
    hf_repo_id: str | None = None,
    hf_token: str | None = None,
    verify_remote: Callable[..., bool] = verify_remote_manifest,
    fyi_cli_args: Sequence[str] = (),
    instance_id: str = DEFAULT_INSTANCE_ID,
    jurisdiction: str | None = None,
) -> dict[str, Any]:
    """Run one prospective sync and advance state only after verification succeeds."""
    instance = get_instance(instance_id)
    previous_state = load_sync_state(state_path)
    since = previous_state.last_successful_sync

    if dry_run:
        changes = load_changes(changes_path, since)
        materialized = dry_run_materialize_changes(changes, derived_dir)
    else:
        previous_manifest = manifest_path
        if hf_repo_id is not None:
            restore_hf_dataset(
                repo_id=hf_repo_id,
                token=hf_token,
                manifest_dir=manifest_path.parent,
                derived_dir=derived_dir,
            )
            previous_manifest = write_diff_baseline_manifest(
                derived_dir=derived_dir,
                output_path=state_path.parent / "diff_baseline_manifest.json",
            )
        run_fyi_cli_diff(
            since=since,
            derived_dir=derived_dir,
            previous_manifest=previous_manifest,
            output_path=changes_path,
            extra_args=fyi_cli_args,
        )
        changes = load_changes(changes_path, since)
        materialized = 0

    write_changes(changes_path, changes)
    if not dry_run and not changes_have_records(changes) and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = assemble_manifest(
            derived_dir=derived_dir,
            manifest_path=manifest_path,
            parquet_path=parquet_path,
            authorities_path=authorities_path,
            fyi_cli_version=fyi_cli_version,
            instance_id=instance.id,
            jurisdiction=jurisdiction,
        )
    manifest_sha256 = sha256_file(manifest_path)

    sync_has_changes = changes_have_records(changes)
    revision = None
    verified = True
    if hf_repo_id is not None:
        if sync_has_changes and not dry_run:
            if hf_token is None:
                msg = "HF token is required to publish prospective sync changes"
                raise RuntimeError(msg)
            commit_info = publish_sync_to_hf(
                repo_id=hf_repo_id,
                token=hf_token,
                manifest_dir=manifest_path.parent,
                derived_dir=derived_dir,
            )
            revision = getattr(commit_info, "oid", None)
        verified = verify_remote(
            repo_id=hf_repo_id,
            local_manifest=manifest_path,
            token=hf_token,
            revision=revision,
        )
    if not verified:
        msg = "Remote manifest SHA-256 verification failed"
        raise RuntimeError(msg)

    new_state = SyncState(
        last_successful_sync=changes["meta"]["generated_at"],
        last_manifest_sha256=manifest_sha256,
        record_count=int(manifest["meta"]["record_count"]),
    )
    write_sync_state(state_path, new_state)
    return {
        "since": since,
        "generated_at": new_state.last_successful_sync,
        "record_count": new_state.record_count,
        "manifest_sha256": manifest_sha256,
        "materialized_records": materialized,
        "verified": verified,
        "instance_id": instance.id,
        "jurisdiction": jurisdiction,
        "rate_limit_name": instance.rate_limit_name,
    }
