"""Historical seed orchestration helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SeedCaps:
    """Hard limits for a seed run."""

    max_requests: int | None = None
    max_bytes: int | None = None
    max_runtime_minutes: float | None = None
    max_disk_gb: float | None = None


@dataclass(frozen=True)
class SeedRequest:
    """Request queued for capture."""

    request_id: int
    url_title: str
    title: str = ""
    authority: str = ""


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(UTC).isoformat()


def load_ledger(ledger_path: Path) -> set[int]:
    """Read completed request IDs from a JSONL ledger."""
    if not ledger_path.exists():
        return set()

    completed: set[int] = set()
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("status") == "completed":
            completed.add(int(entry["request_id"]))
    return completed


def append_ledger(ledger_path: Path, entry: dict[str, Any]) -> None:
    """Append one JSON entry to the seed ledger."""
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def requests_from_jsonl(path: Path) -> list[SeedRequest]:
    """Load request IDs and lightweight metadata from JSONL."""
    requests: list[SeedRequest] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        request_id = int(data["request_id"])
        requests.append(
            SeedRequest(
                request_id=request_id,
                url_title=str(data.get("url_title") or f"request-{request_id}"),
                title=str(data.get("title") or ""),
                authority=str(data.get("authority") or ""),
            ),
        )
    return requests


def synthetic_requests(max_requests: int | None) -> list[SeedRequest]:
    """Create deterministic dry-run request placeholders."""
    count = max_requests or 1
    return [
        SeedRequest(request_id=request_id, url_title=f"dry-run-request-{request_id}")
        for request_id in range(1, count + 1)
    ]


def ensure_disk_budget(path: Path, max_disk_gb: float | None) -> None:
    """Fail early if free disk space is below the configured budget."""
    if max_disk_gb is None:
        return
    path.mkdir(parents=True, exist_ok=True)
    free_bytes = shutil.disk_usage(path).free
    required = int(max_disk_gb * 1024**3)
    if free_bytes < required:
        msg = f"Free disk space {free_bytes} bytes is below required budget {required} bytes"
        raise RuntimeError(msg)


def cap_exceeded(
    *,
    processed: int,
    bytes_written: int,
    started_at: float,
    caps: SeedCaps,
) -> str | None:
    """Return the first exceeded cap name, if any."""
    if caps.max_requests is not None and processed >= caps.max_requests:
        return "max_requests"
    if caps.max_bytes is not None and bytes_written >= caps.max_bytes:
        return "max_bytes"
    if caps.max_runtime_minutes is not None:
        elapsed_minutes = (time.monotonic() - started_at) / 60
        if elapsed_minutes >= caps.max_runtime_minutes:
            return "max_runtime_minutes"
    return None


def dry_run_capture(request: SeedRequest, derived_dir: Path) -> Path:
    """Write a deterministic derived record without network access."""
    derived_dir.mkdir(parents=True, exist_ok=True)
    output_path = derived_dir / f"{request.request_id}.json"
    record = {
        "request_id": request.request_id,
        "url_title": request.url_title,
        "title": request.title or f"Dry-run request {request.request_id}",
        "authority": request.authority,
        "state": "dry-run",
        "html_captured": False,
        "attachments": [],
        "warc_record_ids": [],
        "first_seen": None,
        "last_updated": None,
    }
    output_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def capture_with_fyi_cli(request: SeedRequest, output_dir: Path, extra_args: Sequence[str]) -> None:
    """Delegate one request capture to fyi-cli."""
    command = [
        "fyi-cli",
        "archive",
        "capture",
        "--request-id",
        str(request.request_id),
        "--output-dir",
        str(output_dir),
        *extra_args,
    ]
    subprocess.run(command, check=True)


def run_seed(
    *,
    requests: Iterable[SeedRequest],
    ledger_path: Path,
    data_dir: Path,
    derived_dir: Path,
    caps: SeedCaps,
    dry_run: bool,
    date_from: str | None = None,
    date_to: str | None = None,
    fyi_cli_args: Sequence[str] = (),
) -> dict[str, int | str | None]:
    """Run a resumable historical seed over request records."""
    ensure_disk_budget(data_dir, caps.max_disk_gb)
    completed = load_ledger(ledger_path)
    started_at = time.monotonic()
    processed = 0
    skipped = 0
    bytes_written = 0
    stop_reason: str | None = None

    for request in requests:
        if request.request_id in completed:
            skipped += 1
            continue

        stop_reason = cap_exceeded(
            processed=processed,
            bytes_written=bytes_written,
            started_at=started_at,
            caps=caps,
        )
        if stop_reason is not None:
            break

        if dry_run:
            output_path = dry_run_capture(request, derived_dir)
        else:
            capture_with_fyi_cli(request, data_dir, fyi_cli_args)
            output_path = derived_dir / f"{request.request_id}.json"

        size = output_path.stat().st_size if output_path.exists() else 0
        bytes_written += size
        processed += 1
        append_ledger(
            ledger_path,
            {
                "request_id": request.request_id,
                "status": "completed",
                "bytes_written": size,
                "output_path": output_path.as_posix(),
                "completed_at": utc_now(),
                "date_from": date_from,
                "date_to": date_to,
                "dry_run": dry_run,
            },
        )

    return {
        "processed": processed,
        "skipped": skipped,
        "bytes_written": bytes_written,
        "date_from": date_from,
        "date_to": date_to,
        "stop_reason": stop_reason,
    }
