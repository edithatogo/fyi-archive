from __future__ import annotations

import json
from typing import Self
from urllib.request import Request

import pytest

from fyi_archive.internet_archive_cdx import fetch_complete_cdx


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def test_fetches_all_reported_pages() -> None:
    calls = 0

    def opener(request: Request, timeout: int) -> _Response:
        nonlocal calls
        calls += 1
        url = request.full_url
        if "showNumPages" in url:
            return _Response([["blocks"], ["2"]])
        return _Response([["original"], [f"https://example.test/request/{calls}"]])

    rows = fetch_complete_cdx("example.test/request/*", page_size=10, max_pages=2, opener=opener)
    assert rows[0] == ["original"]
    assert len(rows) == 3


def test_rejects_page_count_over_cap() -> None:
    def opener(_: Request, timeout: int) -> _Response:
        return _Response([["blocks"], ["3"]])

    with pytest.raises(RuntimeError, match="exceeds configured cap"):
        fetch_complete_cdx("example.test/request/*", page_size=10, max_pages=2, opener=opener)


def test_uses_empty_page_terminator_when_cdx_page_count_is_unknown() -> None:
    calls = 0

    def opener(request: Request, timeout: int) -> _Response:
        nonlocal calls
        calls += 1
        if "showNumPages" in request.full_url:
            return _Response([["blocks"], [None]])
        return (
            _Response([["original"], ["https://example.test/request/1"]])
            if calls == 2
            else _Response([])
        )

    assert (
        len(fetch_complete_cdx("example.test/request/*", page_size=10, max_pages=2, opener=opener))
        == 2
    )


def test_all_captures_mode_preserves_versions_without_url_collapse() -> None:
    requests: list[str] = []

    def opener(request: Request, timeout: int) -> _Response:
        requests.append(request.full_url)
        if "showNumPages" in request.full_url:
            return _Response([["blocks"], ["1"]])
        return _Response(
            [
                ["original", "timestamp"],
                ["https://example.test/request/1", "20200101000000"],
                ["https://example.test/request/1", "20210101000000"],
            ]
        )

    rows = fetch_complete_cdx(
        "example.test/request/*",
        page_size=10,
        max_pages=2,
        capture_mode="all_captures",
        opener=opener,
    )

    assert rows[1:] == [
        ["https://example.test/request/1", "20200101000000"],
        ["https://example.test/request/1", "20210101000000"],
    ]
    assert all("collapse=urlkey" not in request for request in requests)


def test_rejects_unknown_capture_mode() -> None:
    with pytest.raises(ValueError, match="unsupported CDX capture mode"):
        fetch_complete_cdx("example.test/request/*", page_size=10, max_pages=2, capture_mode="all")
