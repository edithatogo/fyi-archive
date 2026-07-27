from __future__ import annotations

import json
from email.message import Message
from io import BytesIO
from typing import Self
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from fyi_archive import internet_archive_cdx
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


def test_resumes_from_next_page_and_reports_new_page() -> None:
    requests: list[str] = []
    reported: list[tuple[int, int | None, list[str], list[list[str]], str]] = []

    def opener(request: Request, timeout: int) -> _Response:
        requests.append(request.full_url)
        if "showNumPages" in request.full_url:
            return _Response([["blocks"], ["2"]])
        return _Response([["original"], ["https://example.test/request/2"]])

    prior_rows = [["https://example.test/request/1"]]
    prior_fingerprint = internet_archive_cdx.hashlib.sha256(
        json.dumps(prior_rows, sort_keys=True).encode()
    ).hexdigest()
    rows = fetch_complete_cdx(
        "example.test/request/*",
        page_size=10,
        max_pages=2,
        start_page=1,
        existing_rows=prior_rows,
        expected_header=["original"],
        expected_page_count=2,
        existing_fingerprints={prior_fingerprint},
        page_callback=lambda *values: reported.append(values),
        opener=opener,
    )

    assert rows[1:] == [
        ["https://example.test/request/1"],
        ["https://example.test/request/2"],
    ]
    assert "page=1" in requests[-1]
    assert reported[0][:4] == (
        1,
        2,
        ["original"],
        [["https://example.test/request/2"]],
    )


def test_rejects_resume_when_reported_page_count_changes() -> None:
    def opener(request: Request, timeout: int) -> _Response:
        if "showNumPages" in request.full_url:
            return _Response([["blocks"], ["3"]])
        return _Response([])

    with pytest.raises(RuntimeError, match="page count changed"):
        fetch_complete_cdx(
            "example.test/request/*",
            page_size=10,
            max_pages=3,
            start_page=1,
            expected_page_count=2,
            opener=opener,
        )


def test_rejects_invalid_resume_page_boundaries() -> None:
    with pytest.raises(ValueError, match="start_page"):
        fetch_complete_cdx(
            "example.test/request/*",
            page_size=10,
            max_pages=2,
            start_page=3,
        )

    def opener(request: Request, timeout: int) -> _Response:
        if "showNumPages" in request.full_url:
            return _Response([["blocks"], ["1"]])
        return _Response([])

    with pytest.raises(RuntimeError, match="beyond reported"):
        fetch_complete_cdx(
            "example.test/request/*",
            page_size=10,
            max_pages=2,
            start_page=2,
            opener=opener,
        )


def test_rejects_unknown_capture_mode() -> None:
    with pytest.raises(ValueError, match="unsupported CDX capture mode"):
        fetch_complete_cdx("example.test/request/*", page_size=10, max_pages=2, capture_mode="all")


@pytest.mark.parametrize(
    ("responses", "message"),
    [
        ([["blocks"]], "invalid page count"),
    ],
)
def test_rejects_invalid_or_incomplete_reported_pagination(
    responses: list[object], message: str
) -> None:
    def opener(_: Request, timeout: int) -> _Response:
        return _Response(responses.pop(0))

    with pytest.raises(RuntimeError, match=message):
        fetch_complete_cdx("example.test/request/*", page_size=10, max_pages=2, opener=opener)


def test_rejects_empty_page_before_reported_coverage() -> None:
    responses: list[object] = [
        [["blocks"], ["1"]],
        [],
    ]

    def opener(_: Request, timeout: int) -> _Response:
        return _Response(responses.pop(0))

    with pytest.raises(RuntimeError, match="empty before reported coverage"):
        fetch_complete_cdx("example.test/request/*", page_size=10, max_pages=2, opener=opener)


def test_rejects_unknown_page_count_that_reaches_the_cap() -> None:
    def opener(request: Request, timeout: int) -> _Response:
        if "showNumPages" in request.full_url:
            return _Response([["blocks"], [None]])
        return _Response([["original"], ["https://example.test/request/1"]])

    with pytest.raises(RuntimeError, match="reached configured cap"):
        fetch_complete_cdx("example.test/request/*", page_size=10, max_pages=1, opener=opener)


def test_rejects_changed_headers_and_repeated_pages() -> None:
    calls = 0

    def changed_header(_: Request, timeout: int) -> _Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _Response([["blocks"], ["2"]])
        return _Response([["original" if calls == 2 else "timestamp"], [str(calls)]])

    with pytest.raises(RuntimeError, match="header changed"):
        fetch_complete_cdx(
            "example.test/request/*", page_size=10, max_pages=2, opener=changed_header
        )

    calls = 0

    def repeated_page(_: Request, timeout: int) -> _Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _Response([["blocks"], ["2"]])
        return _Response([["original"], ["https://example.test/request/1"]])

    with pytest.raises(RuntimeError, match="page repeated"):
        fetch_complete_cdx(
            "example.test/request/*", page_size=10, max_pages=2, opener=repeated_page
        )


def test_fetch_rejects_deadlines_and_bounded_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(internet_archive_cdx.time, "monotonic", lambda: 1.0)
    with pytest.raises(RuntimeError, match="whole-run deadline"):
        internet_archive_cdx._fetch([], lambda *_: _Response([]), deadline=1.0)

    monkeypatch.setattr(internet_archive_cdx.time, "monotonic", lambda: 0.0)
    monkeypatch.setattr(internet_archive_cdx.time, "sleep", lambda _: None)

    def unavailable(request: Request, timeout: int) -> _Response:
        raise HTTPError(
            request.full_url, 503, "unavailable", hdrs=Message(), fp=BytesIO(b"unavailable")
        )

    with pytest.raises(RuntimeError, match="bounded retries"):
        internet_archive_cdx._fetch([], unavailable, deadline=10.0)


def test_retries_page_level_http_400_but_not_count_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(internet_archive_cdx.time, "sleep", lambda _: None)
    page_attempts = 0

    def transient_page(request: Request, timeout: int) -> _Response:
        nonlocal page_attempts
        if "showNumPages" in request.full_url:
            return _Response([["blocks"], ["1"]])
        page_attempts += 1
        if page_attempts == 1:
            raise HTTPError(
                request.full_url,
                400,
                "transient CDX page failure",
                hdrs=Message(),
                fp=BytesIO(b""),
            )
        return _Response([["original"], ["https://example.test/request/1"]])

    rows = fetch_complete_cdx(
        "example.test/request/*", page_size=10, max_pages=2, opener=transient_page
    )
    assert len(rows) == 2
    assert page_attempts == 2

    count_attempts = 0

    def invalid_count_query(request: Request, timeout: int) -> _Response:
        nonlocal count_attempts
        count_attempts += 1
        raise HTTPError(request.full_url, 400, "bad query", hdrs=Message(), fp=BytesIO(b""))

    with pytest.raises(HTTPError, match="HTTP Error 400"):
        fetch_complete_cdx(
            "example.test/request/*", page_size=10, max_pages=2, opener=invalid_count_query
        )
    assert count_attempts == 1
