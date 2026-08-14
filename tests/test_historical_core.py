from __future__ import annotations

import json
from pathlib import Path

import pytest

from fyi_archive.historical_core import (
    archive_replay_url,
    failed_archived_request,
    parse_archived_request,
)


def test_archived_request_core_fields_are_extracted() -> None:
    html = Path("tests/fixtures/alaveteli_request.html").read_text(encoding="utf-8")
    record = parse_archived_request(
        html,
        source_url="https://example.test/request/road-safety",
        archive_url="https://web.archive.org/web/20240101id_/https://example.test/request/road-safety",
        archive_timestamp="20240101",
        archive_digest="sha1:abc",
        instance_id="example",
    )
    assert record["title"] == "Road safety records"
    assert record["authority"] == "Example Agency"
    assert record["state"] == "Successful"
    assert record["first_seen"] == "2024-01-02"
    assert record["last_updated"] == "2024-03-04"
    assert record["extraction_status"] == "extracted"
    assert len(record["content_sha256"]) == 64


def test_replay_url_preserves_source_url() -> None:
    url = archive_replay_url("https://example.test/request/a?x=1", "20240101")
    assert url == "https://web.archive.org/web/20240101id_/https://example.test/request/a?x=1"


def test_failed_record_does_not_invent_core_values() -> None:
    record = failed_archived_request(
        source_url="https://example.test/request/a",
        archive_url="https://web.archive.org/web/20240101id_/https://example.test/request/a",
        archive_timestamp="20240101",
        archive_digest="sha1:x",
        diagnostic="timeout",
        instance_id="example",
    )
    assert record["extraction_status"] == "fetch_failed"
    assert record["title"] == ""
    assert record["instance_id"] == "example"


def test_enrichment_script_contract_is_json_serializable() -> None:
    record = failed_archived_request(
        source_url="https://example.test/request/a",
        archive_url="",
        archive_timestamp="",
        archive_digest="",
        diagnostic="missing timestamp",
    )
    assert json.loads(json.dumps(record))["extraction_status"] == "fetch_failed"


def test_archive_replay_url_handles_empty_inputs() -> None:
    url = archive_replay_url("", "")
    assert url == "https://web.archive.org/web/id_/"


def test_archive_replay_url_raises_type_error_on_none() -> None:
    with pytest.raises(TypeError):
        # type: ignore is needed since we're intentionally passing an invalid type
        archive_replay_url(None, "20240101")  # type: ignore[arg-type]


def test_extract_date_handles_missing_tags() -> None:
    from bs4 import BeautifulSoup

    from fyi_archive.historical_core import _extract_date

    soup = BeautifulSoup("<html></html>", "html.parser")
    assert _extract_date(soup, ("datePublished",)) is None


def test_first_text_handles_missing_tags() -> None:
    from bs4 import BeautifulSoup

    from fyi_archive.historical_core import _first_text

    soup = BeautifulSoup("<html></html>", "html.parser")
    assert _first_text(soup, ("h1",)) == ""


def test_first_text_handles_empty_text() -> None:
    from bs4 import BeautifulSoup

    from fyi_archive.historical_core import _first_text

    soup = BeautifulSoup("<h1>  </h1>", "html.parser")
    assert _first_text(soup, ("h1",)) == ""


def test_parse_archived_request_missing_status() -> None:
    html = """
    <html>
        <head><title>Test Title</title></head>
        <body>
            <a class="public-body">Test Body</a>
            <div class="unknown-status">status: open</div>
        </body>
    </html>
    """
    record = parse_archived_request(
        html,
        source_url="https://example.test/request/road-safety",
        archive_url="https://web.archive.org/web/20240101id_/https://example.test/request/road-safety",
        archive_timestamp="20240101",
    )
    assert record["state"] == "open"
