"""Fail-closed, paginated Internet Archive CDX acquisition."""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"


def fetch_complete_cdx(
    url_pattern: str,
    *,
    page_size: int,
    max_pages: int,
    opener: Callable[..., Any] = urllib.request.urlopen,  # noqa: S310
) -> list[list[str]]:
    """Retrieve all reported CDX pages or raise without producing a partial result."""
    base = [
        ("url", url_pattern),
        ("output", "json"),
        ("filter", "statuscode:200"),
        ("fl", "original,timestamp,digest,statuscode,length"),
        ("collapse", "urlkey"),
        ("limit", str(page_size)),
    ]
    pages = _fetch([*base, ("showNumPages", "true")], opener)
    try:
        page_value = pages[1][0]
        page_count = None if page_value is None else int(page_value)
    except (IndexError, TypeError, ValueError) as error:
        raise RuntimeError("CDX returned an invalid page count") from error
    if page_count is not None and (page_count < 0 or page_count > max_pages):
        raise RuntimeError(f"CDX page count {page_count} exceeds configured cap {max_pages}")

    header: list[str] | None = None
    rows: list[list[str]] = []
    fingerprints: set[str] = set()
    page = 0
    while page_count is None or page < page_count:
        if page >= max_pages:
            raise RuntimeError(f"CDX traversal reached configured cap {max_pages} without terminator")
        payload = _fetch([*base, ("page", str(page))], opener)
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
        page += 1
    return [header or ["original", "timestamp", "digest", "statuscode", "length"], *rows]


def _fetch(params: list[tuple[str, str]], opener: Callable[..., Any]) -> Any:  # noqa: ANN401
    request = urllib.request.Request(  # noqa: S310
        f"{CDX_ENDPOINT}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": "fyi-archive-cdx-paginator/1.0"},
    )
    with opener(request, timeout=60) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))
