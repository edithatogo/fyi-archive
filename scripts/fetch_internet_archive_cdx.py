"""Fetch a paginated, hash-preserving Internet Archive CDX export."""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

CDX_URL = "https://web.archive.org/cdx/search/cdx"
DEFAULT_FIELDS = "original,timestamp,digest,statuscode,mimetype"


def _request_json(params: list[tuple[str, str]], *, user_agent: str, retries: int, backoff: float, opener: Callable[..., Any] = urllib.request.urlopen, sleep: Callable[[float], None] = time.sleep) -> Any:
    url = f"{CDX_URL}?{urllib.parse.urlencode(params)}"
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": user_agent})
            with opener(request, timeout=60) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            last_error = error
            if attempt < retries:
                sleep(backoff * (2**attempt))
    raise RuntimeError(f"CDX request failed after {retries + 1} attempts: {last_error}")


def fetch_cdx(url_pattern: str, *, limit: int, max_pages: int | None = None, retries: int = 4, backoff: float = 5.0, user_agent: str = "fyi-archive-cdx-paginator/1.0", opener: Callable[..., Any] = urllib.request.urlopen, sleep: Callable[[float], None] = time.sleep) -> list[list[str]]:
    common = [("url", url_pattern), ("output", "json"), ("filter", "statuscode:200"), ("filter", "mimetype:text/html"), ("fl", DEFAULT_FIELDS), ("collapse", "digest"), ("limit", str(limit))]
    if "*" not in url_pattern:
        common.insert(1, ("matchType", "prefix"))
    count_payload = _request_json(common + [("showNumPages", "true")], user_agent=user_agent, retries=retries, backoff=backoff, opener=opener, sleep=sleep)
    try:
        page_value = count_payload[1][0]
        if page_value is None:
            raise ValueError("CDX returned a null page count")
        page_count = int(page_value)
    except (IndexError, TypeError, ValueError) as error:
        raise ValueError(f"CDX showNumPages response is invalid: {error}") from error
    page_count = min(page_count, max_pages) if max_pages is not None else page_count
    header: list[str] | None = None
    rows: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for page in range(page_count):
        payload = _request_json(common + [("page", str(page))], user_agent=user_agent, retries=retries, backoff=backoff, opener=opener, sleep=sleep)
        if not isinstance(payload, list) or not payload:
            continue
        if header is None:
            header = [str(value) for value in payload[0]]
        page_rows = payload[1:] if payload[0] == header else payload
        for row in page_rows:
            normalized = tuple(str(value) for value in row)
            if normalized not in seen:
                seen.add(normalized)
                rows.append(list(normalized))
    return [header or ["original", "timestamp", "digest", "statuscode", "mimetype"]] + rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url-pattern", required=True)
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--backoff", type=float, default=5.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.limit < 1 or args.retries < 0 or (args.max_pages is not None and args.max_pages < 1):
        raise SystemExit("limit/retries/max-pages values are invalid")
    payload = fetch_cdx(args.url_pattern, limit=args.limit, max_pages=args.max_pages, retries=args.retries, backoff=args.backoff)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(payload) - 1, "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
