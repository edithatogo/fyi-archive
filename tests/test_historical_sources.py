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
        json.dumps([
            ["original", "timestamp", "digest"],
            ["https://www.righttoknow.org.au/request/example", "20180101", "sha1:A"],
            ["https://www.righttoknow.org.au/request/other", "20180102", "sha1:B"],
        ]),
        encoding="utf-8",
    )
    merged = merge_historical_sources([
        load_historical_source(morph, "morph"),
        load_historical_source(cdx, "internet_archive_cdx"),
    ])
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
        json.dumps([
            {"original": "https://example.test/request/a"},
            ["https://example.test/request/b"],
            ["not-a-url", "2020"],
            "ignored",
        ]),
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


def test_alaveteli_json_feed_preserves_instance_and_metadata(tmp_path: Path) -> None:
    path = tmp_path / "feed.json"
    path.write_text(
        json.dumps({
            "entries": [
                {
                    "id": 42,
                    "url": "https://example.test/request/example",
                    "title": "A request",
                    "public_body": {"name": "Agency"},
                    "state": "successful",
                }
            ]
        }),
        encoding="utf-8",
    )
    document = load_historical_source(path, "alaveteli_feed_json", instance_id="example")
    assert document["records"][0]["instance_id"] == "example"
    assert document["records"][0]["authority"] == "Agency"


def test_alaveteli_atom_feed_is_normalized(tmp_path: Path) -> None:
    path = tmp_path / "feed.xml"
    path.write_text(
        """<feed xmlns="http://www.w3.org/2005/Atom">
          <entry><id>tag:example.test,2026:1</id><title>Request</title>
          <updated>2026-07-12T00:00:00Z</updated>
          <link href="https://example.test/request/one" /></entry>
        </feed>""",
        encoding="utf-8",
    )
    document = load_historical_source(path, "alaveteli_atom", instance_id="example")
    assert document["record_count"] == 1
    assert document["records"][0]["source"] == "alaveteli_atom"
    assert document["records"][0]["instance_id"] == "example"


@pytest.mark.parametrize("source_kind", ["official_dataset", "operator_export"])
def test_structured_exports_support_json_and_preserve_source_kind(
    tmp_path: Path, source_kind: str
) -> None:
    path = tmp_path / f"{source_kind}.json"
    path.write_text(
        json.dumps({
            "results": [
                {
                    "request_id": "42",
                    "request_url": "https://example.test/request/42",
                    "subject": "A request",
                    "public_body_name": "Agency",
                    "status": "successful",
                },
                {"subject": "No public URL"},
            ]
        }),
        encoding="utf-8",
    )
    document = load_historical_source(path, source_kind, instance_id="example")
    assert document["record_count"] == 1
    assert document["records"][0]["source"] == source_kind
    assert document["records"][0]["authority"] == "Agency"


def test_structured_csv_supports_tabular_operator_export(tmp_path: Path) -> None:
    path = tmp_path / "export.csv"
    path.write_text(
        "id,url,title,authority\n42,https://example.test/request/42,Request,Agency\n",
        encoding="utf-8",
    )
    document = load_historical_source(path, "operator_export")
    assert document["record_count"] == 1
    assert document["records"][0]["source_record_id"] == "42"


def test_structured_exports_support_nested_records_and_authority_dict(tmp_path: Path) -> None:
    path = tmp_path / "nested.json"
    path.write_text(
        json.dumps({
            "data": {
                "records": [
                    {
                        "id": 7,
                        "url": "https://example.test/request/7",
                        "authority": {"url_name": "agency"},
                        "name": "Nested request",
                    }
                ]
            }
        }),
        encoding="utf-8",
    )
    document = load_historical_source(path, "official_dataset")
    assert document["record_count"] == 1
    assert document["records"][0]["authority"] == "agency"


def test_structured_exports_reject_scalar_json(tmp_path: Path) -> None:
    path = tmp_path / "scalar.json"
    path.write_text("42", encoding="utf-8")
    with pytest.raises(ValueError, match="object or array"):
        load_historical_source(path, "official_dataset")


def test_structured_tsv_uses_tab_delimiter(tmp_path: Path) -> None:
    path = tmp_path / "export.tsv"
    path.write_text(
        "id\trequest_url\ttitle\n42\thttps://example.test/request/42\tRequest\n",
        encoding="utf-8",
    )
    document = load_historical_source(path, "operator_export")
    assert document["record_count"] == 1
