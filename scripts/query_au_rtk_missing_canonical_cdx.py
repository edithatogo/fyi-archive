"""Query CDX metadata for exact canonical URLs of the 858 excluded AU RTK slugs."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from scripts.prepare_au_rtk_replay_selection import (
    APPROVED_CDX_SHA256,
    HEADER,
    build_selection,
    sha256_file,
)

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
EXPECTED_MISSING_SLUGS = 858
EXPECTED_QUERY_COUNT = 1_716


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
            queries.append(
                {
                    "canonical_slug": slug,
                    "media_kind": media_kind,
                    "exact_url": f"https://www.righttoknow.org.au/request/{slug}{suffix}",
                }
            )
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
        if (
            actual.scheme not in {"http", "https"}
            or (actual.hostname or "").lower() != (expected.hostname or "").lower()
            or actual.path != expected.path
            or actual.query
            or actual.fragment
        ):
            raise ValueError("CDX response escaped the authorized exact canonical URL")
        if row[3] != "200":
            raise ValueError("CDX response contains a non-success capture")
        validated.append(row)
    return validated


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
            result = {
                **query,
                "status": "complete",
                "retrieved_at": datetime.now(UTC).isoformat(),
                "record_count": len(records),
                "records": records,
                "request_url": str(response.request.url),
                "response_sha256": hashlib.sha256(response.content).hexdigest(),
            }
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            checkpoint.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
            return result  # noqa: TRY300
        except Exception as error:  # noqa: BLE001
            last_error = str(error)[-500:]
            if attempt < retries:
                time.sleep(2**attempt)
    result = {**query, "status": "failed", "diagnostic": last_error, "records": []}
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
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
    results = []
    pending = []
    for query in plan["queries"]:
        key = f"{query['canonical_slug']}.{query['media_kind']}"
        checkpoint = output_root / "responses" / f"{key}.json"
        if checkpoint.is_file():
            existing = json.loads(checkpoint.read_text(encoding="utf-8"))
            if existing.get("status") == "complete":
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
    results.sort(key=lambda item: (item["canonical_slug"], item["media_kind"]))
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
    return {
        **{key: value for key, value in candidate.items() if key != "results"},
        "candidate_sha256": sha256_file(candidate_path),
    }


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
