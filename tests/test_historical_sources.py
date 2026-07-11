from __future__ import annotations

import json
from pathlib import Path

import pytest

from fyi_archive.historical_sources import load_historical_source, merge_historical_sources


def test_morph_csv_is_normalized_with_checksum(tmp_path: Path) -> None:
    path = tmp_path / "morph.csv"
    path.write_text(
        "request_url,title,public_body_name,display_status,created_at\n"
        "https://www.righttoknow.org.au/request/example,Example,Agency,Successful,2018-01-01\n",
        encoding="utf-8",
    )
    document = load_historical_source(path, "morph")
    assert document["record_count"] == 1
    assert len(document["sha256"]) == 64
    assert document["records"][0]["authority"] == "Agency"


def test_cdx_array_and_morph_rows_deduplicate_by_url(tmp_path: Path) -> None:
    morph = tmp_path / "morph.csv"
    morph.write_text(
        "request_url,title\nhttps://www.righttoknow.org.au/request/example,Historical\n",
        encoding="utf-8",
    )
    cdx = tmp_path / "cdx.json"
    cdx.write_text(
        json.dumps(
            [
                ["original", "timestamp", "digest"],
                ["https://www.righttoknow.org.au/request/example", "20180101", "sha1:A"],
                ["https://www.righttoknow.org.au/request/other", "20180102", "sha1:B"],
            ]
        ),
        encoding="utf-8",
    )
    merged = merge_historical_sources(
        [
            load_historical_source(morph, "morph"),
            load_historical_source(cdx, "internet_archive_cdx"),
        ]
    )
    assert merged["record_count"] == 2
    assert merged["records"][0]["title"] == "Historical"


def test_rejects_unknown_source_kind(tmp_path: Path) -> None:
    path = tmp_path / "input"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        load_historical_source(path, "unknown")


def test_skips_invalid_morph_urls(tmp_path: Path) -> None:
    path = tmp_path / "morph.csv"
    path.write_text("request_url,title\nnot-a-url,Ignored\n", encoding="utf-8")
    assert load_historical_source(path, "morph")["record_count"] == 0


def test_cdx_supports_dict_rows_and_short_lists(tmp_path: Path) -> None:
    path = tmp_path / "cdx.json"
    path.write_text(
        json.dumps(
            [
                {"original": "https://example.test/request/a"},
                ["https://example.test/request/b"],
                ["not-a-url", "2020"],
                "ignored",
            ]
        ),
        encoding="utf-8",
    )
    document = load_historical_source(path, "internet_archive_cdx")
    assert document["record_count"] == 2
    assert document["records"][0]["archive_digest"] == ""


def test_rejects_non_array_cdx_payload(tmp_path: Path) -> None:
    path = tmp_path / "cdx.json"
    path.write_text(json.dumps({"rows": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="JSON array"):
        load_historical_source(path, "internet_archive_cdx")
