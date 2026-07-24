"""Fetch a paginated, hash-preserving Internet Archive CDX export."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

CDX_URL = "https://web.archive.org/cdx/search/cdx"
DEFAULT_FIELDS = "original,timestamp,digest,statuscode,mimetype"
PAGE_WORKERS = 4


def _curl_json(
    params: list[tuple[str, str]],
    *,
    user_agent: str,
    timeout: float,
) -> Any:  # noqa: ANN401
    url = f"{CDX_URL}?{urllib.parse.urlencode(params)}"
    command = [
        "curl",
        "--fail-with-body",
        "--silent",
        "--show-error",
        "--location",
        "--http1.1",
        "--max-time",
        str(timeout),
        "--user-agent",
        user_agent,
        url,
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, check=True, text=True, timeout=timeout + 5
        )  # noqa: S603
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"CDX curl request failed: {error}") from error
    return json.loads(result.stdout)


def _request_json(
    params: list[tuple[str, str]],
    *,
    user_agent: str,
    retries: int,
    backoff: float,
    opener: Callable[..., Any] = urllib.request.urlopen,  # noqa: S310
    sleep: Callable[[float], None] = time.sleep,
    transport: str = "urllib",
    timeout: float = 60.0,
) -> Any:  # noqa: ANN401
    url = f"{CDX_URL}?{urllib.parse.urlencode(params)}"
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            if transport == "curl":
                return _curl_json(params, user_agent=user_agent, timeout=timeout)
            request = urllib.request.Request(url, headers={"User-Agent": user_agent})  # noqa: S310
            with opener(request, timeout=timeout) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, RuntimeError) as error:
            last_error = error
            if attempt < retries:
                sleep(backoff * (2**attempt))
    raise RuntimeError(f"CDX request failed after {retries + 1} attempts: {last_error}")


def fetch_cdx(
    url_pattern: str,
    *,
    limit: int,
    max_pages: int | None = None,
    retries: int = 4,
    backoff: float = 5.0,
    user_agent: str = "fyi-archive-cdx-paginator/1.0",
    opener: Callable[..., Any] = urllib.request.urlopen,  # noqa: S310
    sleep: Callable[[float], None] = time.sleep,
    transport: str = "urllib",
    timeout: float = 60.0,
) -> list[list[str]]:
    common = [
        ("url", url_pattern),
        ("output", "json"),
        ("filter", "statuscode:200"),
        ("filter", "mimetype:text/html"),
        ("fl", DEFAULT_FIELDS),
        ("collapse", "digest"),
        ("limit", str(limit)),
    ]
    if "*" not in url_pattern:
        common.insert(1, ("matchType", "prefix"))
    count_payload = _request_json(
        [*common, ("showNumPages", "true")],
        user_agent=user_agent,
        retries=retries,
        backoff=backoff,
        opener=opener,
        sleep=sleep,
        transport=transport,
        timeout=timeout,
    )
    try:
        page_value = count_payload[1][0]
        page_count = None if page_value is None else int(page_value)
    except (IndexError, TypeError, ValueError):
        page_count = None
    page_cap = max_pages if max_pages is not None else 30
    if page_count is not None:
        page_count = min(page_count, page_cap)
    header: list[str] | None = None
    rows: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    seen_page_fingerprints: set[tuple[tuple[str, ...], ...]] = set()

    def fetch_page(page: int) -> Any:  # noqa: ANN401
        return _request_json(
            [*common, ("page", str(page))],
            user_agent=user_agent,
            retries=retries,
            backoff=backoff,
            opener=opener,
            sleep=sleep,
            transport=transport,
            timeout=timeout,
        )

    def process_page(payload: Any) -> bool:  # noqa: ANN401
        nonlocal header
        if not isinstance(payload, list) or len(payload) <= 1:
            return False
        if header is None:
            header = [str(value) for value in payload[0]]
        page_rows = payload[1:] if payload[0] == header else payload
        page_fingerprint = tuple(tuple(str(value) for value in row) for row in page_rows)
        if page_fingerprint in seen_page_fingerprints:
            raise RuntimeError("CDX page payload repeated before coverage completed")
        seen_page_fingerprints.add(page_fingerprint)
        for row in page_rows:
            normalized = tuple(str(value) for value in row)
            if normalized not in seen:
                seen.add(normalized)
                rows.append(list(normalized))
        return True

    page = 0
    while page_count is None or page < page_count:
        batch_end = min(page + PAGE_WORKERS, page_count or page_cap)
        page_numbers = range(page, batch_end)
        with ThreadPoolExecutor(max_workers=min(PAGE_WORKERS, len(page_numbers))) as executor:
            payloads = list(executor.map(fetch_page, page_numbers))
        for payload in payloads:
            if not process_page(payload) and page_count is None:
                return [
                    header or ["original", "timestamp", "digest", "statuscode", "mimetype"],
                    *rows,
                ]
        page = batch_end
        if page_count is None and page >= page_cap:
            raise RuntimeError(
                f"CDX page count unavailable and bounded page cap {page_cap} was reached"
            )
    return [header or ["original", "timestamp", "digest", "statuscode", "mimetype"], *rows]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url-pattern", required=True)
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--backoff", type=float, default=5.0)
    parser.add_argument("--transport", choices=("urllib", "curl"), default="urllib")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (
        args.limit < 1
        or args.retries < 0
        or args.timeout <= 0
        or (args.max_pages is not None and args.max_pages < 1)
    ):
        raise SystemExit("limit/retries/max-pages values are invalid")
    payload = fetch_cdx(
        args.url_pattern,
        limit=args.limit,
        max_pages=args.max_pages,
        retries=args.retries,
        backoff=args.backoff,
        transport=args.transport,
        timeout=args.timeout,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(payload) - 1, "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
