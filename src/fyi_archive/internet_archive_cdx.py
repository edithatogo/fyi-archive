"""Fail-closed, paginated Internet Archive CDX acquisition."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
CAPTURE_MODES = frozenset({"url_index", "all_captures"})


def fetch_complete_cdx(
    url_pattern: str,
    *,
    page_size: int,
    max_pages: int,
    capture_mode: str = "url_index",
    max_runtime_seconds: float = 180.0,
    opener: Callable[..., Any] = urllib.request.urlopen,  # noqa: S310
    start_page: int = 0,
    existing_rows: list[list[str]] | None = None,
    expected_header: list[str] | None = None,
    expected_page_count: int | None = None,
    existing_fingerprints: set[str] | None = None,
    page_callback: Callable[[int, int | None, list[str], list[list[str]], str], None] | None = None,
) -> list[list[str]]:
    """Retrieve a complete CDX view, optionally resuming verified page evidence."""
    if capture_mode not in CAPTURE_MODES:
        raise ValueError(f"unsupported CDX capture mode: {capture_mode}")
    if start_page < 0 or start_page > max_pages:
        raise ValueError("start_page must be within the configured page cap")
    deadline = time.monotonic() + max_runtime_seconds
    base = [
        ("url", url_pattern),
        ("output", "json"),
        ("filter", "statuscode:200"),
        ("fl", "original,timestamp,digest,statuscode,length"),
        ("limit", str(page_size)),
    ]
    if capture_mode == "url_index":
        base.append(("collapse", "urlkey"))
    pages = _fetch([*base, ("showNumPages", "true")], opener, deadline=deadline)
    try:
        page_value = pages[1][0]
        page_count = None if page_value is None else int(page_value)
    except (IndexError, TypeError, ValueError) as error:
        raise RuntimeError("CDX returned an invalid page count") from error
    if page_count is not None and (page_count < 0 or page_count > max_pages):
        raise RuntimeError(f"CDX page count {page_count} exceeds configured cap {max_pages}")
    if expected_page_count is not None and page_count != expected_page_count:
        raise RuntimeError("CDX reported page count changed since the checkpoint was created")

    if page_count is not None and start_page > page_count:
        raise RuntimeError("checkpoint starts beyond reported CDX coverage")

    header = list(expected_header) if expected_header is not None else None
    rows = [list(row) for row in existing_rows] if existing_rows is not None else []
    fingerprints = set(existing_fingerprints or ())
    page = start_page
    while page_count is None or page < page_count:
        if page >= max_pages:
            raise RuntimeError(
                f"CDX traversal reached configured cap {max_pages} without terminator"
            )
        payload = _fetch([*base, ("page", str(page))], opener, deadline=deadline)
        if not isinstance(payload, list) or not payload or len(payload) == 1:
            if page_count is None:
                break
            raise RuntimeError(f"CDX page {page} was empty before reported coverage completed")
        current_header = [str(value) for value in payload[0]]
        if header is None:
            header = current_header
        elif current_header != header:
            raise RuntimeError("CDX page header changed during acquisition")
        page_rows = [[str(value) for value in row] for row in payload[1:]]
        fingerprint = hashlib.sha256(json.dumps(page_rows, sort_keys=True).encode()).hexdigest()
        if fingerprint in fingerprints:
            raise RuntimeError("CDX page repeated during acquisition")
        fingerprints.add(fingerprint)
        rows.extend(page_rows)
        if page_callback is not None:
            page_callback(page, page_count, current_header, page_rows, fingerprint)
        page += 1
    return [header or ["original", "timestamp", "digest", "statuscode", "length"], *rows]


def _fetch(params: list[tuple[str, str]], opener: Callable[..., Any], *, deadline: float) -> Any:  # noqa: ANN401
    request = urllib.request.Request(  # noqa: S310
        f"{CDX_ENDPOINT}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": "fyi-archive-cdx-paginator/1.0"},
    )
    page_query = any(key == "page" for key, _ in params)
    last_error: Exception | None = None
    for attempt in range(5):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError("CDX acquisition exceeded whole-run deadline")
        try:
            with opener(request, timeout=min(60, remaining)) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            retryable_page_error = page_query and error.code == 400
            if error.code not in {429, 500, 502, 503, 504} and not retryable_page_error:
                raise
            last_error = error
        except (json.JSONDecodeError, TimeoutError, URLError, OSError) as error:
            last_error = error
        if attempt < 4:
            time.sleep(min(2 ** (attempt + 1), max(0, deadline - time.monotonic())))
    raise RuntimeError(f"CDX request failed after bounded retries: {last_error}")
