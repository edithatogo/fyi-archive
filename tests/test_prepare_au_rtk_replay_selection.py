from __future__ import annotations

import pytest

from scripts.prepare_au_rtk_replay_selection import (
    HEADER,
    build_selection,
    validate_authorized_counts,
)


def test_selection_prefers_latest_json_then_html_fallback() -> None:
    rows = [
        HEADER,
        ["https://www.righttoknow.org.au/request/a", "20200101", "A", "200", "1"],
        ["https://www.righttoknow.org.au/request/a.json", "20200102", "B", "200", "1"],
        ["https://www.righttoknow.org.au/request/a.json", "20200103", "C", "200", "1"],
        ["https://www.righttoknow.org.au/request/b", "20200104", "D", "200", "1"],
        ["https://www.righttoknow.org.au/request/b/response/1", "20200105", "E", "200", "1"],
    ]
    result = build_selection(rows, cdx_sha256="0" * 64)
    assert [record["canonical_slug"] for record in result["records"]] == ["a", "b"]
    assert result["records"][0]["archive_digest"] == "C"
    assert result["records"][0]["media_kind"] == "json"
    assert result["records"][1]["media_kind"] == "html"


def test_selection_rejects_bad_header_or_row() -> None:
    with pytest.raises(ValueError, match="header"):
        build_selection([["bad"]], cdx_sha256="0" * 64)
    with pytest.raises(ValueError, match="malformed"):
        build_selection([HEADER, ["not", "all", "fields"]], cdx_sha256="0" * 64)


def test_authorized_counts_fail_closed_for_fixture() -> None:
    with pytest.raises(ValueError, match="authorized counts mismatch"):
        validate_authorized_counts({"record_count": 2, "json_count": 1, "html_fallback_count": 1})
