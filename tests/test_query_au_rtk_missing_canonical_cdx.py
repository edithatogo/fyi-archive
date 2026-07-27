from scripts.query_au_rtk_missing_canonical_cdx import CDX_ENDPOINT


def test_completion_endpoint_is_internet_archive_only() -> None:
    assert CDX_ENDPOINT == "https://web.archive.org/cdx/search/cdx"
