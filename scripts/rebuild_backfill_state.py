#!/usr/bin/env python3
"""Rebuild compacted FYI backfill state from GitHub Actions history."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backfill_state import refresh_summary  # ty: ignore[unresolved-import]


def run_gh(args: list[str]) -> str:
    completed = subprocess.run(
        ["gh", *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout


def gh_json(args: list[str]) -> dict[str, Any] | list[dict[str, Any]]:
    return cast("dict[str, Any] | list[dict[str, Any]]", json.loads(run_gh(args)))


def load_state_by_issue_number(*, repo: str, issue_number: int) -> dict[str, Any]:
    body = cast(
        "dict[str, Any]",
        gh_json(["api", f"repos/{repo}/issues/{issue_number}"]),
    )
    body = str(body["body"])
    state = json.loads(str(body))
    if not isinstance(state, dict):
        raise ValueError("state issue body must be a JSON object")
    return state


def successful_merge_runs(*, repo: str, limit: int = 500) -> list[dict[str, Any]]:
    runs = cast(
        "list[dict[str, Any]]",
        gh_json([
            "run",
            "list",
            "--repo",
            repo,
            "--workflow",
            "merge_backfill_artifacts.yml",
            "--status",
            "success",
            "--limit",
            str(limit),
            "--json",
            "databaseId,createdAt,updatedAt",
        ]),
    )
    runs.sort(key=lambda item: str(item.get("createdAt") or ""))
    return runs


def merged_batch_snapshot(*, repo: str, merge_run: dict[str, Any]) -> dict[str, Any] | None:
    merge_run_id = int(merge_run["databaseId"])
    merge_artifacts = artifact_names(repo=repo, run_id=merge_run_id)
    source_run_name = next(
        (name for name in merge_artifacts if name.startswith("merged-backfill-")),
        None,
    )
    if source_run_name is None:
        return None
    source_run_id = int(source_run_name.removeprefix("merged-backfill-"))
    source_artifacts = artifact_names(repo=repo, run_id=source_run_id)
    labels = [
        name.removeprefix("historical-backfill-")
        for name in source_artifacts
        if name.startswith("historical-backfill-")
    ]
    if not labels:
        return None

    with tempfile.TemporaryDirectory() as temp_dir:
        manifest_path = download_artifact(
            repo=repo,
            run_id=merge_run_id,
            pattern=source_run_name,
            destination=Path(temp_dir),
        )
        merged_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        record_count = int(merged_manifest.get("meta", {}).get("record_count") or 0)

    return {
        "labels": labels,
        "record_count": record_count,
    }


def artifact_names(*, repo: str, run_id: int) -> list[str]:
    payload = cast(
        "dict[str, Any]",
        gh_json(["api", f"repos/{repo}/actions/runs/{run_id}/artifacts"]),
    )
    artifacts = payload.get("artifacts") or []
    return [
        str(item.get("name"))
        for item in artifacts
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    ]


def download_artifact(*, repo: str, run_id: int, pattern: str, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "gh",
            "run",
            "download",
            str(run_id),
            "--repo",
            repo,
            "--pattern",
            pattern,
            "--dir",
            destination.as_posix(),
        ],
        check=True,
    )
    manifests = sorted(destination.glob("**/manifests/latest_manifest.json"))
    if not manifests:
        msg = f"no manifest found after downloading {pattern!r} from run {run_id}"
        raise ValueError(msg)
    return manifests[0]


def batch_span_from_label(label: str) -> tuple[int, int]:
    start_str, end_str = label.split("-", 1)
    return int(start_str), int(end_str)


def canonicalize_state(*, state: dict[str, Any], repo: str) -> dict[str, Any]:
    batches = state.get("batches") or []
    if not isinstance(batches, list):
        raise ValueError("state batches must be a list")
    id_from = int(state.get("id_from") or 1)
    id_to = int(state.get("id_to") or 0)
    if id_to < id_from:
        raise ValueError("state id_to must be >= id_from")

    batch_map: dict[str, dict[str, Any]] = {}
    for batch in batches:
        if not isinstance(batch, dict):
            continue
        label = str(batch.get("label") or "")
        if not label:
            continue
        normalized = dict(batch)
        normalized["id_from"] = str(int(normalized["id_from"]))
        normalized["id_to"] = str(int(normalized["id_to"]))
        normalized["label"] = label
        normalized.setdefault("status", "pending")
        batch_map[label] = normalized

    merged_labels_seen: set[str] = set()
    merge_runs = successful_merge_runs(repo=repo)
    max_parallel = min(20, max(1, len(merge_runs)))

    with ThreadPoolExecutor(max_workers=max_parallel) as executor:
        future_to_run = {
            executor.submit(merged_batch_snapshot, repo=repo, merge_run=run): run
            for run in merge_runs
        }
        for future in as_completed(future_to_run):
            snapshot = future.result()
            if snapshot is None:
                continue
            labels = list(snapshot["labels"])
            if not labels:
                continue
            record_count = int(snapshot["record_count"])

            merged_labels_seen.update(labels)
            for index, label in enumerate(labels):
                start, end = batch_span_from_label(label)
                normalized = dict(
                    batch_map.get(
                        label,
                        {"id_from": str(start), "id_to": str(end), "label": label},
                    ),
                )
                normalized["id_from"] = str(start)
                normalized["id_to"] = str(end)
                normalized["label"] = label
                normalized["status"] = "merged"
                if index == 0:
                    normalized["record_count"] = record_count
                else:
                    normalized.setdefault("record_count", 0)
                batch_map[label] = normalized

    rebuilt_batches = sorted(
        batch_map.values(),
        key=lambda batch: (
            int(batch["id_from"]),
            int(batch["id_to"]),
            str(batch.get("label") or ""),
        ),
    )

    rebuilt_state = dict(state)
    rebuilt_state["batches"] = rebuilt_batches
    pending_batches = [
        batch for batch in rebuilt_batches if str(batch.get("status") or "pending") != "merged"
    ]
    rebuilt_state["next_id"] = int(pending_batches[0]["id_from"]) if pending_batches else id_to + 1
    rebuilt_state["complete"] = not pending_batches and rebuilt_state["next_id"] > id_to
    rebuilt_state = refresh_summary(rebuilt_state, id_to=id_to)
    rebuilt_state["id_from"] = id_from
    rebuilt_state["id_to"] = id_to
    return rebuilt_state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--issue-number", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.issue_number is None:
        msg = "issue lookup by label is disabled while GraphQL is rate limited; pass --issue-number"
        raise SystemExit(msg)
    issue_number = int(args.issue_number)
    state = load_state_by_issue_number(repo=args.repo, issue_number=issue_number)
    rebuilt = canonicalize_state(state=state, repo=args.repo)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rebuilt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"issue_number": issue_number, "summary": rebuilt.get("summary", {})},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
