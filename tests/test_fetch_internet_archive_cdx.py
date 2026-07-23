import json

from scripts.fetch_internet_archive_cdx import fetch_cdx


class _Response:
    def __init__(self, payload: object):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def test_fetches_pages_deduplicates_rows_and_retries() -> None:
    calls = []
    failures = {"data": 1}

    def opener(request, timeout):
        calls.append(request.full_url)
        if "showNumPages" in request.full_url:
            return _Response([["numpages"], ["2"]])
        if "page=0" in request.full_url:
            return _Response([["original", "timestamp"], ["/a", "1"], ["/a", "1"]])
        if failures["data"]:
            failures["data"] = 0
            raise OSError("503")
        return _Response([["original", "timestamp"], ["/a", "1"], ["/b", "2"]])

    result = fetch_cdx("example.test/request", limit=10, retries=1, backoff=0, opener=opener, sleep=lambda _seconds: None)
    assert result == [["original", "timestamp"], ["/a", "1"], ["/b", "2"]]
    assert len(calls) == 4


def test_wildcard_scope_omits_incompatible_match_type() -> None:
    seen = []

    def opener(request, timeout):
        seen.append(request.full_url)
        if "showNumPages" in request.full_url:
            return _Response([["numpages"], ["1"]])
        return _Response([["original"], ["/a"]])

    fetch_cdx("example.test/request/*", limit=10, retries=0, opener=opener)
    assert all("matchType=prefix" not in url for url in seen)


def test_fetch_can_bound_pages() -> None:
    def opener(request, timeout):
        if "showNumPages" in request.full_url:
            return _Response([["numpages"], ["5"]])
        return _Response([["original"], [request.full_url]])

    result = fetch_cdx("example.test/request", limit=10, max_pages=1, retries=0, opener=opener)
    assert len(result) == 2


def test_null_page_count_is_a_fail_closed_error() -> None:
    calls = []

    def opener(request, timeout):
        calls.append(request.full_url)
        if "showNumPages" in request.full_url:
            return _Response([["numpages"], [None]])
        return _Response([["original"], ["/a"]]) if len(calls) == 2 else _Response([["original"]])

    result = fetch_cdx("example.test/request", limit=10, retries=0, opener=opener)
    assert result == [["original"], ["/a"]]


def test_repeated_page_payload_fails_closed_when_page_count_is_unknown() -> None:
    def opener(request, timeout):
        if "showNumPages" in request.full_url:
            return _Response([["numpages"], [None]])
        return _Response([["original"], ["/same"]])

    try:
        fetch_cdx("example.test/request", limit=10, retries=0, opener=opener)
    except RuntimeError as error:
        assert str(error) == "CDX page payload repeated before coverage completed"
    else:
        raise AssertionError("repeated CDX pages must fail closed")
