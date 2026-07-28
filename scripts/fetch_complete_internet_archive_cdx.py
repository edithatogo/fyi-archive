"""Write a complete CDX export and immutable acquisition evidence manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fyi_archive.internet_archive_cdx import (
    CAPTURE_MODES,
    CDX_ENDPOINT,
    fetch_complete_cdx_with_resume_key,
)


def _write_json(path: Path, value: dict[str, object]) -> None:
    """Write an evidence record, creating only its requested parent directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _config_hash(args: argparse.Namespace, *, include_max_pages: bool = False) -> str:
    config = {
        "url_pattern": args.url_pattern,
        "instance_id": args.instance_id,
        "host": args.host,
        "page_size": args.page_size,
        **({"max_pages": args.max_pages} if include_max_pages else {}),
        "capture_mode": args.capture_mode,
        "pagination_mode": "resume_key",
        "endpoint": CDX_ENDPOINT,
    }
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def _checkpoint_dir(output: Path) -> Path:
    return output.with_name(f"{output.stem}.pages")


def _load_checkpoint(
    directory: Path, *, config_sha256: str, legacy_config_sha256: str | None = None
) -> tuple[int, str | None, list[str] | None, list[list[str]], set[str]]:
    state_path = directory / "checkpoint.json"
    if not state_path.exists():
        return 0, None, None, [], set()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("config_sha256") not in {config_sha256, legacy_config_sha256}:
        raise RuntimeError("checkpoint configuration does not match this export")
    completed_pages = int(state["completed_pages"])
    next_resume_key = state.get("next_resume_key")
    header: list[str] | None = None
    rows: list[list[str]] = []
    fingerprints: set[str] = set()
    for page in range(completed_pages):
        page_path = directory / f"page-{page:06d}.json"
        if not page_path.exists():
            raise RuntimeError(f"checkpoint page {page} is missing")
        payload: dict[str, Any] = json.loads(page_path.read_text(encoding="utf-8"))
        if payload.get("page") != page:
            raise RuntimeError(f"checkpoint page {page} has an invalid index")
        current_header = [str(value) for value in payload["header"]]
        page_rows = [[str(value) for value in row] for row in payload["rows"]]
        fingerprint = hashlib.sha256(json.dumps(page_rows, sort_keys=True).encode()).hexdigest()
        if payload.get("fingerprint") != fingerprint or fingerprint in fingerprints:
            raise RuntimeError(f"checkpoint page {page} failed fingerprint validation")
        if header is None:
            header = current_header
        elif header != current_header:
            raise RuntimeError("checkpoint page headers are inconsistent")
        rows.extend(page_rows)
        fingerprints.add(fingerprint)
    return completed_pages, next_resume_key, header, rows, fingerprints


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url-pattern", required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--capture-mode", choices=sorted(CAPTURE_MODES), default="url_index")
    parser.add_argument("--max-runtime-seconds", type=float, default=180.0)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from hash-verified resume-key chunks beside the output path",
    )
    parser.add_argument("--resume-source-run-id")
    args = parser.parse_args()
    if bool(args.resume_source_run_id) != args.resume:
        parser.error("--resume and --resume-source-run-id must be supplied together")
    retrieved_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    base_evidence: dict[str, object] = {
        "provider": "Internet Archive CDX",
        "instance_id": args.instance_id,
        "host": args.host,
        "endpoint": CDX_ENDPOINT,
        "url_pattern": args.url_pattern,
        "capture_mode": args.capture_mode,
        "pagination_mode": "resume_key",
        "retrieved_at": retrieved_at,
        "eligible_for_empirical_freeze": False,
        "publication": False,
        "redistribution": False,
        "resume_source_run_id": args.resume_source_run_id,
    }
    checkpoint_dir = _checkpoint_dir(args.output)
    config_sha256 = _config_hash(args)
    legacy_config_sha256 = _config_hash(args, include_max_pages=True)
    if not args.resume and checkpoint_dir.exists():
        shutil.rmtree(checkpoint_dir)
    start_chunk, next_resume_key, header, existing_rows, fingerprints = _load_checkpoint(
        checkpoint_dir,
        config_sha256=config_sha256,
        legacy_config_sha256=legacy_config_sha256,
    )
    checkpoint_record_count = len(existing_rows)
    print(
        json.dumps(
            {
                "event": "cdx-start",
                "instance_id": args.instance_id,
                "start_chunk": start_chunk,
                "record_count": checkpoint_record_count,
                "resumed": args.resume,
            },
            sort_keys=True,
        ),
        flush=True,
    )

    def save_page(
        page: int,
        resume_key: str | None,
        current_header: list[str],
        page_rows: list[list[str]],
        fingerprint: str,
    ) -> None:
        nonlocal checkpoint_record_count
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        _write_json(
            checkpoint_dir / f"page-{page:06d}.json",
            {
                "page": page,
                "header": current_header,
                "rows": page_rows,
                "fingerprint": fingerprint,
            },
        )
        checkpoint_record_count += len(page_rows)
        _write_json(
            checkpoint_dir / "checkpoint.json",
            {
                "schema_version": "2.0",
                "config_sha256": config_sha256,
                "completed_pages": page + 1,
                "next_page": page + 1,
                "next_resume_key": resume_key,
                "record_count": checkpoint_record_count,
            },
        )
        print(
            json.dumps(
                {
                    "event": "cdx-checkpoint",
                    "instance_id": args.instance_id,
                    "completed_chunks": page + 1,
                    "record_count": checkpoint_record_count,
                    "next_resume_key_sha256": (
                        hashlib.sha256(resume_key.encode()).hexdigest() if resume_key else None
                    ),
                },
                sort_keys=True,
            ),
            flush=True,
        )

    try:
        rows = fetch_complete_cdx_with_resume_key(
            args.url_pattern,
            page_size=args.page_size,
            max_pages=args.max_pages,
            capture_mode=args.capture_mode,
            max_runtime_seconds=args.max_runtime_seconds,
            start_chunk=start_chunk,
            resume_key=next_resume_key,
            existing_rows=existing_rows,
            expected_header=header,
            existing_fingerprints=fingerprints,
            chunk_callback=save_page,
        )
    except Exception as error:
        checkpoint = _load_checkpoint(checkpoint_dir, config_sha256=config_sha256)
        completed_pages, failed_resume_key, _, partial_rows, _ = checkpoint
        _write_json(
            args.evidence,
            {
                **base_evidence,
                "retrieval_status": "failed",
                "pagination_complete": False,
                "response_sha256": None,
                "record_count": len(partial_rows),
                "checkpoint": {
                    "config_sha256": config_sha256,
                    "completed_pages": completed_pages,
                    "next_page": completed_pages,
                    "page_count": None,
                    "next_resume_key": failed_resume_key,
                    "resumable": completed_pages > 0,
                },
                "failure": {"type": type(error).__name__, "message": str(error)},
            },
        )
        raise
    raw = json.dumps(rows, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(raw, encoding="utf-8")
    evidence = {
        **base_evidence,
        "retrieval_status": "complete",
        "response_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "record_count": len(rows) - 1,
        "pagination_complete": True,
        "checkpoint": {
            "config_sha256": config_sha256,
            "completed_pages": len(list(checkpoint_dir.glob("page-*.json"))),
            "page_count": len(list(checkpoint_dir.glob("page-*.json"))),
            "next_resume_key": None,
            "resumable": False,
        },
    }
    _write_json(args.evidence, evidence)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
