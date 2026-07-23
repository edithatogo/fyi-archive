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
