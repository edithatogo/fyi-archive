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

from fyi_archive.publish.evidence import archive_publication_version
from fyi_archive.publish.hf_publish import sha256_file
from fyi_archive.publish.verification import manifest_record_count
from fyi_archive.publish.zenodo_publish import ZENODO_API, deposition_artifacts, get_deposition


def utc_now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)


def gh_json(args: list[str]) -> dict[str, Any] | list[dict[str, Any]]:
    """Run gh with JSON output and return the parsed payload."""
    completed = subprocess.run(
        ["gh", *args],
        check=True,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    return cast("dict[str, Any] | list[dict[str, Any]]", json.loads(completed.stdout))


def load_controller_state(
    *, repo: str, state_label: str, issue_number: int | None = None
) -> dict[str, Any]:
    """Load the active backfill controller issue body and metadata."""
    if issue_number is None:
        state_title = f"FYI historical backfill state ({state_label})"
        issues = cast(
            "list[dict[str, Any]]",
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
                    "100",
                    "--json",
                    "number,url,title",
                ],
            ),
        )
        issue = next((item for item in issues if item.get("title") == state_title), None)
        if issue is None:
            issues = cast(
                "list[dict[str, Any]]",
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
                        "100",
                        "--json",
                        "number,url,title",
                    ],
                ),
            )
            issue = next((item for item in issues if item.get("title") == state_title), None)
        if issue is None:
            msg = f"no issue found for backfill state label {state_label!r}"
            raise ValueError(msg)
        issue_number = int(issue["number"])
        issue_url = str(issue.get("url") or "")
        issue_title = str(issue.get("title") or "")
    else:
        issue = cast(
            "dict[str, Any]",
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
        issue_url = str(issue.get("url") or "")
        issue_title = str(issue.get("title") or "")

    body_payload = cast(
        "dict[str, Any]",
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
    body = body_payload["body"]
    try:
        state = json.loads(body)
    except json.JSONDecodeError as exc:
        msg = f"backfill state issue {issue_number} does not contain JSON state"
        raise ValueError(msg) from exc
    if not isinstance(state, dict):
        msg = f"backfill state issue {issue_number} must contain a JSON object"
        raise ValueError(msg)
    return {
        "issue_number": issue_number,
        "issue_url": issue_url,
        "issue_title": issue_title,
        "state": state,
    }


def batch_requested_ids(batch: dict[str, Any]) -> int:
    """Return the inclusive ID span covered by one batch."""
    return max(0, int(batch.get("id_to") or 0) - int(batch.get("id_from") or 0) + 1)


def _batch_range(batch: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": str(batch.get("label") or ""),
        "id_from": int(batch.get("id_from") or 0),
        "id_to": int(batch.get("id_to") or 0),
        "record_count": int(batch.get("record_count") or 0),
        "worker_run_id": batch.get("worker_run_id"),
    }


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
    merged_batch_ranges = [_batch_range(batch) for batch in merged_batches]
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
        "merged_batch_ranges": merged_batch_ranges,
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
    response = httpx.get(manifest_url, timeout=60)
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


def manifest_request_ids(manifest_path: Path) -> list[int] | None:
    """Return manifest request IDs when the manifest carries per-request records."""
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    requests = data.get("requests")
    if not isinstance(requests, list):
        return None
    request_ids: list[int] = []
    for record in requests:
        if not isinstance(record, dict):
            continue
        request_id = record.get("request_id")
        if isinstance(request_id, int):
            request_ids.append(request_id)
    return sorted(set(request_ids))


def ids_outside_ranges(
    request_ids: list[int] | None, ranges: list[dict[str, Any]]
) -> list[int] | None:
    """Return published request IDs outside controller-merged batch ranges."""
    if request_ids is None:
        return None
    normalized_ranges = [
        (int(item.get("id_from") or 0), int(item.get("id_to") or 0)) for item in ranges
    ]
    outside: list[int] = []
    for request_id in request_ids:
        if not any(start <= request_id <= end for start, end in normalized_ranges):
            outside.append(request_id)
    return outside


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
    published_request_ids = manifest_request_ids(merged_manifest_path)
    outside_controller = ids_outside_ranges(
        published_request_ids,
        controller["merged_batch_ranges"],
    )
    controller_coverage_verified = outside_controller is not None
    outside_controller_count = None if outside_controller is None else len(outside_controller)
    hf_records = int(hf_info["record_count"]) if hf_info else None
    zenodo_records = int(zenodo_info["record_count"]) if zenodo_info else None
    published_ids_match_controller = outside_controller_count in (None, 0)
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
            "published_request_ids": None
            if published_request_ids is None
            else len(published_request_ids),
            "published_ids_outside_controller_merged_ranges": outside_controller_count,
            "published_ids_outside_controller_sample": None
            if outside_controller is None
            else outside_controller[:25],
        },
        "published": {
            "huggingface": hf_info,
            "zenodo": zenodo_info,
        },
        "comparison": {
            "captured_minus_merged": controller["captured_records"] - merged_records,
            "merged_minus_huggingface": None if hf_records is None else merged_records - hf_records,
            "merged_minus_zenodo": None
            if zenodo_records is None
            else merged_records - zenodo_records,
            "captured_matches_merged": controller["captured_records"] == merged_records,
            "controller_coverage_verified": controller_coverage_verified,
            "published_ids_match_controller_ranges": published_ids_match_controller,
            "merged_matches_huggingface": hf_records is None or merged_records == hf_records,
            "merged_matches_zenodo": zenodo_records is None or merged_records == zenodo_records,
            "fully_verified": (
                controller["captured_records"] == merged_records
                and published_ids_match_controller
                and (hf_records is None or merged_records == hf_records)
                and (zenodo_records is None or merged_records == zenodo_records)
            ),
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
