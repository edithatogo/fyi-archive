"""Replay an exact hash-pinned RightToKnow selection from Internet Archive only."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from fyi_archive.historical_core import archive_replay_url, parse_archived_request

SELECTION_SHA256 = "a1c2308ecc81de3754f37b3c26f7ba7fc232ff5bac930b86b36fb10463178c51"
MAX_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5


def sha256_bytes(value: bytes) -> str:
    """Return the SHA-256 digest of bytes."""
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _assert_archive_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != "web.archive.org":
        raise ValueError(f"redirect escaped Internet Archive: {url}")


def fetch_archive_only(
    client: httpx.Client,
    replay_url: str,
    *,
    timeout_seconds: float,
) -> tuple[bytes, str, str]:
    """Fetch one replay while refusing redirects outside Internet Archive."""
    current = replay_url
    for _ in range(MAX_REDIRECTS + 1):
        _assert_archive_url(current)
        with client.stream(
            "GET",
            current,
            timeout=timeout_seconds,
            headers={"User-Agent": "fyi-archive-au-rtk-replay/1.0"},
        ) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                if not location:
                    raise ValueError("archive redirect lacks Location")
                current = urljoin(current, location)
                continue
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > MAX_BYTES:
                    raise ValueError("archive response exceeds 2 MiB bound")
            return bytes(content), response.headers.get("content-type", ""), current
    raise ValueError("archive redirect limit exceeded")


def _parse_json(
    raw: bytes,
    *,
    selected: dict[str, str],
    replay_url: str,
) -> dict[str, Any]:
    value = json.loads(raw.decode("utf-8"))
    authority = value.get("public_body") or value.get("authority") or {}
    if isinstance(authority, dict):
        authority_name = str(authority.get("name") or "")
        authority_slug = str(authority.get("url_name") or "")
        tags = authority.get("tags") or []
    else:
        authority_name = str(authority)
        authority_slug = ""
        tags = []
    return {
        "source_url": selected["source_url"],
        "archive_url": replay_url,
        "archive_timestamp": selected["archive_timestamp"],
        "archive_digest": selected["archive_digest"],
        "request_key": selected["canonical_slug"],
        "title": str(value.get("title") or ""),
        "authority": authority_name,
        "authority_slug": authority_slug,
        "authority_tags": [
            str(tag[0] if isinstance(tag, list) and tag else tag)
            for tag in tags
            if isinstance(tag, (str, list))
        ]
        if isinstance(tags, list)
        else [],
        "state": str(value.get("state") or value.get("described_state") or ""),
        "law_used": str(value.get("law_used") or ""),
        "first_seen": value.get("created_at") or value.get("date_created"),
        "last_updated": value.get("updated_at") or value.get("date_updated"),
        "request_id": value.get("id"),
        "extraction_status": "extracted",
        "content_sha256": sha256_bytes(raw),
        "extracted_at": datetime.now(UTC).isoformat(),
        "instance_id": "au-rtk",
        "media_kind": "json",
        "parser_version": 2,
    }


def replay_one(
    selected: dict[str, str],
    *,
    output_root: Path,
    timeout_seconds: float,
    retries: int,
) -> dict[str, Any]:
    """Replay and checkpoint one exact selected capture."""
    slug = selected["canonical_slug"]
    replay_url = archive_replay_url(selected["source_url"], selected["archive_timestamp"])
    raw_suffix = ".json" if selected["media_kind"] == "json" else ".html"
    raw_path = output_root / "raw" / f"{slug}{raw_suffix}"
    record_path = output_root / "records" / f"{slug}.json"
    last_error = ""
    for attempt in range(retries + 1):
        try:
            with httpx.Client(follow_redirects=False) as client:
                raw, content_type, final_url = fetch_archive_only(
                    client, replay_url, timeout_seconds=timeout_seconds
                )
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(raw)
            if selected["media_kind"] == "json":
                record = _parse_json(raw, selected=selected, replay_url=final_url)
            else:
                html = raw.decode("utf-8", errors="replace")
                record = parse_archived_request(
                    html,
                    source_url=selected["source_url"],
                    archive_url=final_url,
                    archive_timestamp=selected["archive_timestamp"],
                    archive_digest=selected["archive_digest"],
                    instance_id="au-rtk",
                )
                record["media_kind"] = "html"
                body_link = BeautifulSoup(html, "html.parser").select_one("a[href*='/body/']")
                body_path = urlsplit(str(body_link.get("href") or "")).path if body_link else ""
                record["authority_slug"] = (
                    body_path.split("/body/", 1)[1].split("/", 1)[0]
                    if "/body/" in body_path
                    else ""
                )
                record["authority_tags"] = []
                record["law_used"] = ""
                record["parser_version"] = 2
            record.update(
                {
                    "status": "captured",
                    "byte_count": len(raw),
                    "raw_sha256": sha256_bytes(raw),
                    "content_type": content_type,
                    "selection_reason": selected["selection_reason"],
                }
            )
            record_path.parent.mkdir(parents=True, exist_ok=True)
            record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
            return record  # noqa: TRY300
        except Exception as error:  # noqa: BLE001
            last_error = str(error)[-500:]
            if attempt < retries:
                time.sleep(2**attempt)
    failed = {
        **selected,
        "status": "fetch_failed",
        "extraction_status": "fetch_failed",
        "archive_url": replay_url,
        "diagnostic": last_error,
        "instance_id": "au-rtk",
    }
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(failed, indent=2, sort_keys=True) + "\n")
    return failed


def run(
    selection_path: Path,
    *,
    output_root: Path,
    workers: int,
    launch_delay_seconds: float,
    timeout_seconds: float,
    retries: int,
    circuit_breaker_failures: int,
) -> dict[str, Any]:
    """Replay a selection with deterministic membership and resumable checkpoints."""
    if sha256_file(selection_path) != SELECTION_SHA256:
        raise ValueError("selection SHA-256 mismatch")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    records = selection["records"]
    if selection.get("record_count") != 2_082 or len(records) != 2_082:
        raise ValueError("selection record count mismatch")
    output_root.mkdir(parents=True, exist_ok=True)
    complete: list[dict[str, Any]] = []
    pending: list[dict[str, str]] = []
    for selected in records:
        record_path = output_root / "records" / f"{selected['canonical_slug']}.json"
        if record_path.is_file():
            existing = json.loads(record_path.read_text(encoding="utf-8"))
            if existing.get("status") == "captured" and existing.get("parser_version") == 2:
                complete.append(existing)
                continue
        pending.append(selected)

    circuit_open = False
    if workers == 1:
        consecutive_failures = 0
        for selected in pending:
            result = replay_one(
                selected,
                output_root=output_root,
                timeout_seconds=timeout_seconds,
                retries=retries,
            )
            complete.append(result)
            if result.get("status") == "captured":
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= max(1, circuit_breaker_failures):
                    circuit_open = True
                    break
            time.sleep(max(0.0, launch_delay_seconds))
    else:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            futures = []
            for selected in pending:
                futures.append(
                    executor.submit(
                        replay_one,
                        selected,
                        output_root=output_root,
                        timeout_seconds=timeout_seconds,
                        retries=retries,
                    )
                )
                time.sleep(max(0.0, launch_delay_seconds))
            for future in as_completed(futures):
                complete.append(future.result())

    complete.sort(key=lambda record: str(record.get("request_key") or record["canonical_slug"]))
    normalized = output_root / "normalized-candidate.jsonl"
    normalized.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in complete),
        encoding="utf-8",
    )
    summary = {
        "schema": "fyi-archive.au-rtk-replay-result.v1",
        "status": "candidate_non_final",
        "selection_sha256": SELECTION_SHA256,
        "record_count": len(complete),
        "captured_count": sum(record.get("status") == "captured" for record in complete),
        "failed_count": sum(record.get("status") != "captured" for record in complete),
        "pending_count": selection["record_count"] - len(complete),
        "circuit_open": circuit_open,
        "normalized_candidate_sha256": sha256_file(normalized),
        "publication": False,
        "redistribution": False,
        "manifest_finalization_authorized": False,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (output_root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--launch-delay-seconds", type=float, default=0.25)
    parser.add_argument("--timeout-seconds", type=float, default=30)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--circuit-breaker-failures", type=int, default=5)
    args = parser.parse_args()
    summary = run(
        args.selection,
        output_root=args.output_root,
        workers=args.workers,
        launch_delay_seconds=args.launch_delay_seconds,
        timeout_seconds=args.timeout_seconds,
        retries=args.retries,
        circuit_breaker_failures=args.circuit_breaker_failures,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["failed_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
