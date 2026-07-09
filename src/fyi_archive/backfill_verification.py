"""Backfill dispatch/capture/merge/publication verification report."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import httpx
from huggingface_hub import snapshot_download

from fyi_archive.backfill_state_codec import decode_state
from fyi_archive.publish.evidence import archive_publication_version
from fyi_archive.publish.hf_publish import sha256_file
from fyi_archive.publish.verification import manifest_record_count
from fyi_archive.publish.zenodo_publish import ZENODO_API, deposition_artifacts, get_deposition

LOCAL_BACKFILL_STATE_PATHS = (
    Path("versions/latest_backfill_controller_state.json"),
    Path("versions/2026-07/backfill_controller_state.json"),
    Path("versions/latest_backfill_state.json"),
)


def utc_now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)


def gh_json(args: list[str]) -> dict[str, object] | list[dict[str, object]]:
    """Run gh with JSON output and return the parsed payload."""
    completed = subprocess.run(
        ["gh", *args],
        check=True,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    return cast("dict[str, object] | list[dict[str, object]]", json.loads(completed.stdout))


def load_controller_state(
    *, repo: str, state_label: str, issue_number: int | None = None
) -> dict[str, Any]:
    """Load the active backfill controller issue body and metadata."""
    local_snapshot = os.environ.get("BACKFILL_STATE_SNAPSHOT")
    if local_snapshot:
        snapshot_path = Path(local_snapshot)
        if snapshot_path.exists():
            data = json.loads(snapshot_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "state" in data:
                return data
            if isinstance(data, dict):
                return {
                    "issue_number": issue_number or 0,
                    "issue_url": data.get("issue_url") or "",
                    "issue_title": data.get("issue_title") or "",
                    "state": data,
                }
    if issue_number is None:
        issue_list = cast(
            "list[dict[str, object]]",
            gh_json(
                [
                    "issue",
                    "list",
                    "--repo",
                    repo,
                    "--label",
                    state_label,
                    "--state",
                    "open",
                    "--limit",
                    "1",
                    "--json",
                    "number,url,title",
                ],
            ),
        )
        if not issue_list:
            issue_list = cast(
                "list[dict[str, object]]",
                gh_json(
                    [
                        "issue",
                        "list",
                        "--repo",
                        repo,
                        "--label",
                        state_label,
                        "--state",
                        "all",
                        "--limit",
                        "1",
                        "--json",
                        "number,url,title",
                    ],
                ),
            )
        if not issue_list:
            msg = f"no issue found for backfill state label {state_label!r}"
            raise ValueError(msg)
        first_issue = issue_list[0]
        issue_number = int(str(first_issue["number"]))
        issue_url = str(first_issue.get("url") or "")
        issue_title = str(first_issue.get("title") or "")
    else:
        issue_obj = cast(
            "dict[str, object]",
            gh_json(
                [
                    "issue",
                    "view",
                    str(issue_number),
                    "--repo",
                    repo,
                    "--json",
                    "body,url,title,number",
                ],
            ),
        )
        issue_url = str(issue_obj.get("url") or "")
        issue_title = str(issue_obj.get("title") or "")

    body_payload = cast(
        "dict[str, object]",
        gh_json(
            [
                "issue",
                "view",
                str(issue_number),
                "--repo",
                repo,
                "--json",
                "body",
            ],
        ),
    )
    body = str(body_payload["body"])
    try:
        state = decode_state(body)
    except (json.JSONDecodeError, ValueError) as exc:
        msg = f"backfill state issue {issue_number} does not contain JSON state"
        raise ValueError(msg) from exc
    return {
        "issue_number": issue_number,
        "issue_url": issue_url,
        "issue_title": issue_title,
        "state": state,
    }


def batch_requested_ids(batch: dict[str, Any]) -> int:
    """Return the inclusive ID span covered by one batch."""
    return max(0, int(batch.get("id_to") or 0) - int(batch.get("id_from") or 0) + 1)


def controller_summary(state_info: dict[str, Any]) -> dict[str, Any]:
    """Summarize controller state into report-friendly counts."""
    state = state_info["state"]
    batches = [batch for batch in state.get("batches") or [] if isinstance(batch, dict)]
    dispatched_runs = [entry for entry in state.get("dispatched") or [] if isinstance(entry, dict)]
    worker_runs = sorted(
        {
            str(batch.get("worker_run_id"))
            for batch in batches
            if isinstance(batch.get("worker_run_id"), str) and batch.get("worker_run_id")
        },
    )
    pending_batches = [
        batch for batch in batches if str(batch.get("status") or "pending") == "pending"
    ]
    merged_batches = [batch for batch in batches if str(batch.get("status") or "") == "merged"]
    captured_records = sum(int(batch.get("record_count") or 0) for batch in merged_batches)
    dispatched_requested_ids = sum(batch_requested_ids(batch) for batch in batches)
    return {
        "state_issue_number": state_info["issue_number"],
        "state_issue_url": state_info["issue_url"],
        "state_issue_title": state_info["issue_title"],
        "state_label": state.get("state_label") or state.get("label") or None,
        "id_from": int(state.get("id_from") or 0),
        "id_to": int(state.get("id_to") or 0),
        "complete": bool(state.get("complete")),
        "next_id": int(state.get("next_id") or 0),
        "dispatched_runs": len(dispatched_runs),
        "dispatched_batches": len(batches),
        "dispatched_requested_ids": dispatched_requested_ids,
        "pending_batches": len(pending_batches),
        "merged_batches": len(merged_batches),
        "captured_records": captured_records,
        "worker_runs": worker_runs,
    }


def remote_huggingface_record_count(
    *, repo_id: str, token: str | None, revision: str | None = None
) -> dict[str, Any]:
    """Fetch the published HF manifest and return its record count."""
    with tempfile.TemporaryDirectory() as cache_dir:
        snapshot_path = Path(
            snapshot_download(
                repo_id=repo_id,
                repo_type="dataset",
                token=token,
                revision=revision,
                allow_patterns="manifests/latest_manifest.json",
                cache_dir=cache_dir,
                force_download=True,
            ),
        )
        manifest_path = snapshot_path / "manifests" / "latest_manifest.json"
        return {
            "repo_id": repo_id,
            "revision": revision,
            "manifest_path": manifest_path.as_posix(),
            "manifest_sha256": sha256_file(manifest_path),
            "record_count": manifest_record_count(manifest_path),
        }


def remote_zenodo_record_count(
    *, token: str, deposition_id: int, api_url: str = ZENODO_API
) -> dict[str, Any]:
    """Fetch the published Zenodo manifest and return its record count."""
    deposition = get_deposition(token=token, deposition_id=deposition_id, api_url=api_url)
    manifest_url = None
    for artifact in deposition_artifacts(deposition):
        if artifact.name == "latest_manifest.json" and artifact.url:
            manifest_url = artifact.url
            break
    if manifest_url is None:
        msg = f"Zenodo deposition {deposition_id} does not expose latest_manifest.json"
        raise ValueError(msg)
    response = httpx.get(
        manifest_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    if response.status_code in {401, 403}:
        response = httpx.get(
            manifest_url,
            params={"access_token": token},
            timeout=60,
        )
    response.raise_for_status()
    data = json.loads(response.text)
    return {
        "deposition_id": deposition_id,
        "doi": deposition.get("doi"),
        "api_url": api_url,
        "manifest_url": manifest_url,
        "record_count": int(
            data.get("meta", {}).get("record_count") or data.get("record_count") or 0
        ),
    }


def build_backfill_verification_report(
    *,
    state_info: dict[str, Any],
    merged_manifest_path: Path,
    hf_info: dict[str, Any] | None = None,
    zenodo_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the final backfill verification report."""
    generated_at = utc_now()
    controller = controller_summary(state_info)
    merged_records = manifest_record_count(merged_manifest_path)
    hf_records = int(hf_info["record_count"]) if hf_info else None
    zenodo_records = int(zenodo_info["record_count"]) if zenodo_info else None
    captured_covers_merged = controller["captured_records"] >= merged_records
    mirrors_match = (hf_records is None or merged_records == hf_records) and (
        zenodo_records is None or merged_records == zenodo_records
    )
    return {
        "generated_at": generated_at.isoformat(),
        "archive_publication_version": archive_publication_version(generated_at=generated_at),
        "controller": controller,
        "github_actions": {
            "dispatched_batches": controller["dispatched_batches"],
            "dispatched_requested_ids": controller["dispatched_requested_ids"],
            "captured_records": controller["captured_records"],
            "merged_records": merged_records,
            "worker_runs": controller["worker_runs"],
        },
        "published": {
            "huggingface": hf_info,
            "zenodo": zenodo_info,
        },
        "comparison": {
            "captured_minus_merged": controller["captured_records"] - merged_records,
            "captured_covers_merged": captured_covers_merged,
            "merged_minus_huggingface": None if hf_records is None else merged_records - hf_records,
            "merged_minus_zenodo": None
            if zenodo_records is None
            else merged_records - zenodo_records,
            "captured_matches_merged": controller["captured_records"] == merged_records,
            "merged_matches_huggingface": hf_records is None or merged_records == hf_records,
            "merged_matches_zenodo": zenodo_records is None or merged_records == zenodo_records,
            "fully_verified": captured_covers_merged and mirrors_match,
        },
    }


def write_backfill_report(path: Path, report: dict[str, Any]) -> None:
    """Write a backfill verification report to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_versioned_backfill_report(
    *,
    report: dict[str, Any],
    output_dir: Path = Path("versions"),
) -> None:
    """Write monthly and latest backfill verification reports."""
    publication_month = report["generated_at"][:7]
    month_dir = output_dir / publication_month
    month_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    (month_dir / "backfill_verification.json").write_text(payload, encoding="utf-8")
    (output_dir / "latest_backfill_verification.json").write_text(payload, encoding="utf-8")
