from scripts.filter_historical_request_pages import filter_index, is_canonical_request_url


def test_canonical_request_url_filter_excludes_non_request_material() -> None:
    assert is_canonical_request_url("https://example.test/request/abc")
    assert not is_canonical_request_url("https://example.test/request/abc.json")
    assert not is_canonical_request_url("https://example.test/request/abc/response/1")
    assert not is_canonical_request_url("https://example.test/list/all")


def test_filter_preserves_only_canonical_request_pages() -> None:
    result = filter_index({
        "schema": "historical-source-index-v1",
        "inputs": [{"sha256": "a" * 64}],
        "records": [
            {"source_url": "https://example.test/request/abc"},
            {"source_url": "https://example.test/request/abc.json"},
            {"source_url": "https://example.test/request/abc/response/1"},
        ],
    })
    assert result["record_count"] == 1
    assert result["filter"]["input_record_count"] == 3
    assert result["records"][0]["source_url"].endswith("/request/abc")
