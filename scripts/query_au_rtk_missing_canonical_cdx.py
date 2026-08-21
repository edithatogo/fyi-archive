"""Query CDX metadata for exact canonical URLs of the 858 excluded AU RTK slugs."""

from __future__ import annotations

import argparse
import hashlib
import json
import operator
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, parse_qs, urlsplit

import httpx
import jsonschema

from scripts.prepare_au_rtk_replay_selection import (
    APPROVED_CDX_SHA256,
    HEADER,
    build_selection,
    sha256_file,
)

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
EXPECTED_MISSING_SLUGS = 858
EXPECTED_QUERY_COUNT = 1_716
COMPLETION_SELECTION_SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "schemas"
    / "au-rtk-canonical-completion-replay-selection.schema.json"
)
CDX_QUERY_FIELDS = {
    "matchType": ["exact"],
    "output": ["json"],
    "fl": [",".join(HEADER)],
    "filter": ["statuscode:200"],
}


def _default_port(parsed: SplitResult) -> bool:
    """Return whether a URL has no userinfo and only its scheme's default port."""
    try:
        port = parsed.port
    except ValueError:
        return False
    expected_port = 80 if parsed.scheme == "http" else 443
    return parsed.username is None and parsed.password is None and port in {None, expected_port}


def _is_exact_canonical_url(actual: SplitResult, expected: SplitResult) -> bool:
    """Return whether a CDX URL is exactly the authorized canonical URL."""
    if actual.scheme not in {"http", "https"} or not _default_port(actual):
        return False
    if (actual.hostname or "").lower() != (expected.hostname or "").lower():
        return False
    if actual.path != expected.path:
        return False
    return not actual.query and not actual.fragment


def _atomic_write(path: Path, value: bytes) -> None:
    """Replace one checkpoint artifact atomically within its destination directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary_name = handle.name
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary_name).replace(path)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def build_queries(cdx_rows: list[Any]) -> dict[str, Any]:
    """Build two exact canonical CDX queries for every excluded slug."""
    selection = build_selection(cdx_rows, cdx_sha256=APPROVED_CDX_SHA256)
    selected_slugs = {record["canonical_slug"] for record in selection["records"]}
    all_slugs: set[str] = set()
    for row in cdx_rows[1:]:
        if not isinstance(row, list) or len(row) != len(HEADER):
            raise ValueError("CDX row is malformed")
        from urllib.parse import urlsplit

        parsed = urlsplit(str(row[0]))
        parts = parsed.path.split("/")
        if len(parts) >= 3 and parts[:2] == ["", "request"] and parts[2]:
            leaf = parts[2]
            all_slugs.add(leaf.removesuffix(".json"))
    missing = sorted(all_slugs - selected_slugs)
    if len(missing) != EXPECTED_MISSING_SLUGS:
        raise ValueError(f"excluded slug count mismatch: {len(missing)}")
    queries = []
    for slug in missing:
        for media_kind, suffix in (("json", ".json"), ("html", "")):
            queries.append({
                "canonical_slug": slug,
                "media_kind": media_kind,
                "exact_url": f"https://www.righttoknow.org.au/request/{slug}{suffix}",
            })
    if len(queries) != EXPECTED_QUERY_COUNT:
        raise ValueError("completion query count mismatch")
    return {
        "schema": "fyi-archive.au-rtk-canonical-cdx-query-plan.v1",
        "source_cdx_sha256": APPROVED_CDX_SHA256,
        "missing_slug_count": len(missing),
        "query_count": len(queries),
        "queries": queries,
    }


def validate_response_rows(query: dict[str, str], rows: object) -> list[list[str]]:
    """Validate that CDX returned only the authorized exact canonical URL."""
    if not isinstance(rows, list):
        raise ValueError("CDX response is not an array")
    if not rows:
        return []
    if rows[0] != HEADER:
        raise ValueError("CDX response header mismatch")
    expected = urlsplit(query["exact_url"])
    validated = []
    for row in rows[1:]:
        if (
            not isinstance(row, list)
            or len(row) != len(HEADER)
            or not all(isinstance(value, str) for value in row)
        ):
            raise ValueError("CDX response row is malformed")
        actual = urlsplit(row[0])
        if not _is_exact_canonical_url(actual, expected):
            raise ValueError("CDX response escaped the authorized exact canonical URL")
        if row[3] != "200":
            raise ValueError("CDX response contains a non-success capture")
        validated.append(row)
    return validated


def valid_complete_checkpoint(  # noqa: PLR0911
    query: dict[str, str],
    checkpoint: dict[str, Any],
    *,
    output_root: Path,
) -> bool:
    """Return whether a checkpoint is complete and bound to this exact query."""
    if checkpoint.get("status") != "complete":
        return False
    if any(checkpoint.get(key) != query.get(key) for key in query):
        return False
    records = checkpoint.get("records")
    try:
        validated = validate_response_rows(query, [HEADER, *(records or [])])
    except (TypeError, ValueError):
        return False
    request = urlsplit(str(checkpoint.get("request_url") or ""))
    digest = checkpoint.get("response_sha256")
    filename = checkpoint.get("response_body_filename")
    if not isinstance(filename, str) or Path(filename).name != filename:
        return False
    expected_filename = f"{query['canonical_slug']}.{query['media_kind']}.json"
    if filename != expected_filename:
        return False
    body_path = output_root / "response-bodies" / filename
    if body_path.is_symlink() or not body_path.is_file():
        return False
    body = body_path.read_bytes()
    try:
        body_records = validate_response_rows(query, json.loads(body))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return False
    expected_query = {**CDX_QUERY_FIELDS, "url": [query["exact_url"]]}
    return (
        isinstance(records, list)
        and checkpoint.get("record_count") == len(validated)
        and body_records == validated
        and request.scheme == "https"
        and _default_port(request)
        and (request.hostname or "").lower() == "web.archive.org"
        and request.path == "/cdx/search/cdx"
        and not request.fragment
        and parse_qs(request.query, keep_blank_values=True) == expected_query
        and isinstance(digest, str)
        and len(digest) == 64
        and all(character in "0123456789abcdef" for character in digest)
        and checkpoint.get("response_byte_count") == len(body)
        and hashlib.sha256(body).hexdigest() == digest
    )


def build_completion_replay_selection(
    candidate: dict[str, Any],
    *,
    completion_candidate_sha256: str,
) -> dict[str, Any]:
    """Select latest JSON or HTML captures without authorizing their replay."""
    results = candidate.get("results")
    if (
        not isinstance(results, list)
        or len(results) != EXPECTED_QUERY_COUNT
        or candidate.get("failed_query_count") != 0
        or candidate.get("pending_query_count") != 0
    ):
        raise ValueError("completion candidate is not complete")
    by_slug: dict[str, dict[str, dict[str, Any] | None]] = {}
    for result in results:
        if not isinstance(result, dict) or result.get("status") != "complete":
            raise ValueError("completion result is malformed or incomplete")
        slug = str(result.get("canonical_slug") or "")
        media_kind = str(result.get("media_kind") or "")
        if not slug or media_kind not in {"json", "html"}:
            raise ValueError("completion result identity is invalid")
        options = by_slug.setdefault(slug, {})
        if media_kind in options:
            raise ValueError("completion candidate contains a duplicate slug/media result")
        options[media_kind] = None
        records = result.get("records")
        if not isinstance(records, list):
            raise ValueError("completion result records are invalid")
        validated = validate_response_rows(result, [HEADER, *records])
        if validated:
            latest = max(validated, key=operator.itemgetter(1))
            options[media_kind] = {
                "canonical_slug": slug,
                "media_kind": media_kind,
                "source_url": latest[0],
                "archive_timestamp": latest[1],
                "archive_digest": latest[2],
                "statuscode": latest[3],
                "length": latest[4],
            }
    if len(by_slug) != EXPECTED_MISSING_SLUGS:
        raise ValueError("completion candidate slug count mismatch")
    selected = []
    missing = []
    for slug in sorted(by_slug):
        options = by_slug[slug]
        record = options.get("json") or options.get("html")
        if record is None:
            missing.append(slug)
            continue
        selected.append({
            **record,
            "selection_reason": (
                "latest_successful_canonical_json"
                if record["media_kind"] == "json"
                else "latest_successful_canonical_html_fallback"
            ),
        })
    return {
        "schema": "fyi-archive.au-rtk-canonical-completion-replay-selection.v1",
        "status": "candidate_pending_replay_approval",
        "source_cdx_sha256": APPROVED_CDX_SHA256,
        "completion_candidate_sha256": completion_candidate_sha256,
        "queried_slug_count": len(by_slug),
        "selected_slug_count": len(selected),
        "json_count": sum(record["media_kind"] == "json" for record in selected),
        "html_fallback_count": sum(record["media_kind"] == "html" for record in selected),
        "no_capture_slug_count": len(missing),
        "no_capture_slugs": missing,
        "records": selected,
        "replay_authorized": False,
        "publication": False,
        "redistribution": False,
        "manifest_finalization_authorized": False,
    }


def validate_completion_replay_selection(selection: dict[str, Any]) -> None:
    """Validate exact membership and authorization boundaries of a replay proposal."""
    jsonschema.validate(
        selection,
        json.loads(COMPLETION_SELECTION_SCHEMA.read_text(encoding="utf-8")),
    )
    records = selection["records"]
    missing = selection["no_capture_slugs"]
    selected_slugs = [record["canonical_slug"] for record in records]
    if len(set(selected_slugs)) != len(selected_slugs):
        raise ValueError("completion replay selection contains duplicate slugs")
    if len(set(missing)) != len(missing) or set(selected_slugs) & set(missing):
        raise ValueError("selected and no-capture slug membership overlaps or duplicates")
    if len(selected_slugs) + len(missing) != EXPECTED_MISSING_SLUGS:
        raise ValueError("completion replay selection does not cover all queried slugs")
    if (
        selection["selected_slug_count"] != len(records)
        or selection["no_capture_slug_count"] != len(missing)
        or selection["json_count"] != sum(record["media_kind"] == "json" for record in records)
        or selection["html_fallback_count"]
        != sum(record["media_kind"] == "html" for record in records)
    ):
        raise ValueError("completion replay selection counts are inconsistent")
    for record in records:
        slug = record["canonical_slug"]
        suffix = ".json" if record["media_kind"] == "json" else ""
        parsed = urlsplit(record["source_url"])
        expected = urlsplit(f"https://www.righttoknow.org.au/request/{slug}{suffix}")
        if not _is_exact_canonical_url(parsed, expected):
            raise ValueError("completion replay record escaped its exact canonical URL")


def query_one(
    query: dict[str, str],
    *,
    output_root: Path,
    timeout_seconds: float,
    retries: int,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Fetch one exact-URL CDX response and checkpoint it."""
    key = f"{query['canonical_slug']}.{query['media_kind']}"
    checkpoint = output_root / "responses" / f"{key}.json"
    response_body_path = output_root / "response-bodies" / f"{key}.json"
    last_error = ""
    params = {
        "url": query["exact_url"],
        "matchType": "exact",
        "output": "json",
        "fl": ",".join(HEADER),
        "filter": "statuscode:200",
    }
    for attempt in range(retries + 1):
        try:
            if client is None:
                with httpx.Client(follow_redirects=False) as owned_client:
                    response = owned_client.get(
                        CDX_ENDPOINT,
                        params=params,
                        timeout=timeout_seconds,
                        headers={"User-Agent": "fyi-archive-au-rtk-cdx-completion/1.0"},
                    )
            else:
                response = client.get(
                    CDX_ENDPOINT,
                    params=params,
                    timeout=timeout_seconds,
                    headers={"User-Agent": "fyi-archive-au-rtk-cdx-completion/1.0"},
                )
            response.raise_for_status()
            rows = response.json()
            records = validate_response_rows(query, rows)
            _atomic_write(response_body_path, response.content)
            result = {
                **query,
                "status": "complete",
                "retrieved_at": datetime.now(UTC).isoformat(),
                "record_count": len(records),
                "records": records,
                "request_url": str(response.request.url),
                "response_body_filename": response_body_path.name,
                "response_byte_count": len(response.content),
                "response_sha256": hashlib.sha256(response.content).hexdigest(),
            }
            _atomic_write(
                checkpoint,
                (json.dumps(result, indent=2, sort_keys=True) + "\n").encode(),
            )
            return result  # noqa: TRY300
        except Exception as error:  # noqa: BLE001
            last_error = str(error)[-500:]
            if attempt < retries:
                time.sleep(2**attempt)
    result = {**query, "status": "failed", "diagnostic": last_error, "records": []}
    _atomic_write(
        checkpoint,
        (json.dumps(result, indent=2, sort_keys=True) + "\n").encode(),
    )
    return result


def run(
    plan_path: Path,
    *,
    output_root: Path,
    workers: int,
    launch_delay_seconds: float,
    timeout_seconds: float,
    retries: int,
    circuit_breaker_failures: int,
) -> dict[str, Any]:
    """Execute and consolidate the exact canonical completion plan."""
    plan_sha256 = sha256_file(plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("query_count") != EXPECTED_QUERY_COUNT:
        raise ValueError("query plan count mismatch")
    results: list[dict[str, Any]] = []
    pending: list[dict[str, str]] = []
    for query in plan["queries"]:
        key = f"{query['canonical_slug']}.{query['media_kind']}"
        checkpoint = output_root / "responses" / f"{key}.json"
        if checkpoint.is_file() and not checkpoint.is_symlink():
            try:
                existing = json.loads(checkpoint.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                existing = None
            if isinstance(existing, dict) and valid_complete_checkpoint(
                query,
                existing,
                output_root=output_root,
            ):
                results.append(existing)
                continue
        pending.append(query)
    circuit_open = False
    if workers == 1:
        consecutive_failures = 0
        with httpx.Client(follow_redirects=False) as client:
            for query in pending:
                result = query_one(
                    query,
                    output_root=output_root,
                    timeout_seconds=timeout_seconds,
                    retries=retries,
                    client=client,
                )
                results.append(result)
                if result.get("status") == "complete":
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
            for query in pending:
                futures.append(
                    executor.submit(
                        query_one,
                        query,
                        output_root=output_root,
                        timeout_seconds=timeout_seconds,
                        retries=retries,
                    )
                )
                time.sleep(max(0.0, launch_delay_seconds))
            for future in as_completed(futures):
                results.append(future.result())
    results.sort(key=operator.itemgetter("canonical_slug", "media_kind"))
    candidate = {
        "schema": "fyi-archive.au-rtk-canonical-cdx-completion-candidate.v1",
        "status": "candidate_pending_replay_approval",
        "query_plan_sha256": plan_sha256,
        "query_count": len(results),
        "complete_query_count": sum(item["status"] == "complete" for item in results),
        "failed_query_count": sum(item["status"] != "complete" for item in results),
        "pending_query_count": plan["query_count"] - len(results),
        "circuit_open": circuit_open,
        "urls_with_captures": sum(bool(item.get("records")) for item in results),
        "publication": False,
        "redistribution": False,
        "replay_authorized": False,
        "results": results,
    }
    candidate_path = output_root / "completion-candidate.json"
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n")
    summary = {
        **{key: value for key, value in candidate.items() if key != "results"},
        "candidate_sha256": sha256_file(candidate_path),
    }
    if (
        summary["failed_query_count"] == 0
        and summary["pending_query_count"] == 0
        and summary["query_count"] == EXPECTED_QUERY_COUNT
    ):
        selection = build_completion_replay_selection(
            candidate,
            completion_candidate_sha256=summary["candidate_sha256"],
        )
        validate_completion_replay_selection(selection)
        selection_path = output_root / "completion-replay-selection.candidate.json"
        selection_path.write_text(json.dumps(selection, indent=2, sort_keys=True) + "\n")
        summary.update({
            "completion_replay_selection_sha256": sha256_file(selection_path),
            "completion_replay_selected_slug_count": selection["selected_slug_count"],
            "completion_replay_authorized": False,
        })
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cdx", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--launch-delay-seconds", type=float, default=0.25)
    parser.add_argument("--timeout-seconds", type=float, default=30)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--circuit-breaker-failures", type=int, default=5)
    args = parser.parse_args()
    if sha256_file(args.cdx) != APPROVED_CDX_SHA256:
        raise ValueError("approved CDX SHA-256 mismatch")
    plan = build_queries(json.loads(args.cdx.read_text(encoding="utf-8")))
    args.plan.parent.mkdir(parents=True, exist_ok=True)
    args.plan.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    print(f"query_plan_sha256={sha256_file(args.plan)} queries={plan['query_count']}")
    summary = run(
        args.plan,
        output_root=args.output_root,
        workers=args.workers,
        launch_delay_seconds=args.launch_delay_seconds,
        timeout_seconds=args.timeout_seconds,
        retries=args.retries,
        circuit_breaker_failures=args.circuit_breaker_failures,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["failed_query_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
