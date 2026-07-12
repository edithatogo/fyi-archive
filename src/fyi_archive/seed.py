"""Historical seed orchestration helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CAPTURE_RETRY_ATTEMPTS = 3
CAPTURE_RETRY_BACKOFF_SECONDS = 15.0
TRANSIENT_CAPTURE_ERROR_MARKERS = (
    "httpx.readtimeout",
    "readtimeout",
    "read timeout",
    "timed out",
    "timeout",
    "connection reset",
    "connection aborted",
    "temporarily unavailable",
    "service unavailable",
    "too many requests",
    " 429 ",
    " 500 ",
    " 502 ",
    " 503 ",
    " 504 ",
)


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

    request_id: int | str
    url_title: str
    title: str = ""
    authority: str = ""


class CaptureError(RuntimeError):
    """Raised when fyi-cli capture fails for one request."""

    def __init__(
        self,
        *,
        request_id: int | str,
        command: Sequence[str],
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> None:
        super().__init__(f"fyi-cli capture failed for request {request_id}: exit {returncode}")
        self.request_id = request_id
        self.command = list(command)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def is_transient_capture_error(error: CaptureError) -> bool:
    """Return True when the capture failure looks retryable."""
    error_text = " ".join([error.stdout, error.stderr, str(error)]).lower()
    return any(marker in error_text for marker in TRANSIENT_CAPTURE_ERROR_MARKERS)


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(UTC).isoformat()


def load_ledger(ledger_path: Path) -> set[int | str]:
    """Read completed request IDs from a JSONL ledger."""
    if not ledger_path.exists():
        return set()

    completed: set[int | str] = set()
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("status") == "completed":
            value = entry["request_id"]
            completed.add(int(value) if str(value).isdigit() else str(value))
    return completed


def append_ledger(ledger_path: Path, entry: dict[str, Any]) -> None:
    """Append one JSON entry to the seed ledger."""
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def tail_text(value: str, limit: int = 4000) -> str:
    """Keep ledger failure entries bounded while preserving useful diagnostics."""
    if len(value) <= limit:
        return value
    return value[-limit:]


def requests_from_jsonl(path: Path) -> list[SeedRequest]:
    """Load request IDs and lightweight metadata from JSONL."""
    requests: list[SeedRequest] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        raw_request_id = data["request_id"]
        request_id = int(raw_request_id) if str(raw_request_id).isdigit() else str(raw_request_id)
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


def requests_from_id_range(id_from: int, id_to: int) -> list[SeedRequest]:
    """Create request placeholders from an explicit FYI request ID range."""
    if id_from < 1 or id_to < id_from:
        msg = "Request ID range must be positive and ordered"
        raise ValueError(msg)
    return [
        SeedRequest(request_id=request_id, url_title=f"request-{request_id}")
        for request_id in range(id_from, id_to + 1)
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


def capture_with_fyi_cli(
    request: SeedRequest,
    data_dir: Path,
    dist_dir: Path,
    caps: SeedCaps,
    extra_args: Sequence[str],
) -> dict[str, Any]:
    """Delegate one request capture to fyi-cli."""
    command = [
        sys.executable,
        "-m",
        "fyi_system.cli",
        "capture",
        str(request.request_id),
        "--data-dir",
        str(data_dir),
        "--dist-dir",
        str(dist_dir),
        *extra_args,
    ]
    if caps.max_bytes is not None:
        command.extend(["--max-bytes", str(caps.max_bytes)])
    if caps.max_runtime_minutes is not None:
        command.extend(["--max-runtime-minutes", str(caps.max_runtime_minutes)])
    if caps.max_disk_gb is not None:
        command.extend(["--max-disk-gb", str(caps.max_disk_gb)])
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        raise CaptureError(
            request_id=request.request_id,
            command=command,
            returncode=error.returncode,
            stdout=error.stdout or "",
            stderr=error.stderr or "",
        ) from error
    return json.loads(completed.stdout)


def capture_with_retry(
    request: SeedRequest,
    data_dir: Path,
    dist_dir: Path,
    caps: SeedCaps,
    extra_args: Sequence[str],
    *,
    retry_attempts: int = CAPTURE_RETRY_ATTEMPTS,
    retry_backoff_seconds: float = CAPTURE_RETRY_BACKOFF_SECONDS,
) -> dict[str, Any]:
    """Capture one request with bounded retry for transient upstream failures."""
    attempts = max(1, retry_attempts)
    last_error: CaptureError | None = None

    for attempt in range(1, attempts + 1):
        try:
            return capture_with_fyi_cli(request, data_dir, dist_dir, caps, extra_args)
        except CaptureError as error:
            last_error = error
            if attempt >= attempts or not is_transient_capture_error(error):
                raise
            time.sleep(max(0.0, retry_backoff_seconds) * attempt)

    if last_error is None:
        msg = "capture retry loop exited without a result"
        raise RuntimeError(msg)
    raise last_error


def run_seed(
    *,
    requests: Iterable[SeedRequest],
    ledger_path: Path,
    data_dir: Path,
    derived_dir: Path,
    caps: SeedCaps,
    dry_run: bool,
    dist_dir: Path = Path("dist"),
    date_from: str | None = None,
    date_to: str | None = None,
    fyi_cli_args: Sequence[str] = (),
    min_interval_seconds: float = 0.0,
    continue_on_error: bool = False,
) -> dict[str, int | str | None]:
    """Run a resumable historical seed over request records."""
    ensure_disk_budget(data_dir, caps.max_disk_gb)
    completed = load_ledger(ledger_path)
    started_at = time.monotonic()
    processed = 0
    failed = 0
    skipped = 0
    bytes_written = 0
    stop_reason: str | None = None
    last_capture_at: float | None = None

    for request in requests:
        if request.request_id in completed:
            skipped += 1
            continue

        stop_reason = cap_exceeded(
            processed=processed + failed,
            bytes_written=bytes_written,
            started_at=started_at,
            caps=caps,
        )
        if stop_reason is not None:
            break

        if dry_run:
            output_path = dry_run_capture(request, derived_dir)
        else:
            if last_capture_at is not None:
                remaining = max(0.0, min_interval_seconds - (time.monotonic() - last_capture_at))
                if remaining:
                    time.sleep(remaining)
            try:
                capture_summary = capture_with_retry(
                    request,
                    data_dir,
                    dist_dir,
                    caps,
                    fyi_cli_args,
                )
                last_capture_at = time.monotonic()
            except CaptureError as error:
                last_capture_at = time.monotonic()
                failed += 1
                append_ledger(
                    ledger_path,
                    {
                        "request_id": request.request_id,
                        "status": "failed",
                        "completed_at": utc_now(),
                        "date_from": date_from,
                        "date_to": date_to,
                        "dry_run": dry_run,
                        "error": str(error),
                        "returncode": error.returncode,
                        "command": error.command,
                        "stdout_tail": tail_text(error.stdout),
                        "stderr_tail": tail_text(error.stderr),
                    },
                )
                if continue_on_error:
                    continue
                raise
            output_path = Path(str(capture_summary["derived_path"]))

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
        "failed": failed,
        "skipped": skipped,
        "bytes_written": bytes_written,
        "date_from": date_from,
        "date_to": date_to,
        "stop_reason": stop_reason,
    }
