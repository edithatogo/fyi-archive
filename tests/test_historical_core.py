from __future__ import annotations

import json
from pathlib import Path

import pytest

from fyi_archive.historical_core import (
    archive_replay_url,
    failed_archived_request,
    normalize_alaveteli_state,
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
    assert record["authority_slug"] == "example-agency"
    assert record["law_used"] == ""
    assert record["state"] == "successful"
    assert record["state_text"] == "Successful"
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


def test_archived_display_states_are_conservatively_normalized() -> None:
    examples = {
        "The request was partially successful.": "partially_successful",
        "The request was refused by Example Agency.": "rejected",
        "Example Agency did not have the information requested.": "not_held",
        "The request has been withdrawn by the person who made it.": "user_withdrawn",
        "The request is waiting for clarification.": "waiting_clarification",
        "Waiting for an internal review by Example Agency.": "internal_review",
        "Response to this request is long overdue.": "waiting_response",
        "Currently waiting for a response from Example Agency.": "waiting_response",
    }
    assert {text: normalize_alaveteli_state(text) for text in examples} == examples
    assert normalize_alaveteli_state("We are waiting for the requester to classify it.") == ""


def test_authority_extraction_skips_body_list_navigation() -> None:
    record = parse_archived_request(
        """
        <a href="/body/list/all">View authorities</a>
        <h1>Request</h1>
        <a href="/body/actual-agency">Actual Agency</a>
        """,
        source_url="https://example.test/request/example",
        archive_url="https://web.archive.org/example",
        archive_timestamp="20200101000000",
    )
    assert record["authority"] == "Actual Agency"
    assert record["authority_slug"] == "actual-agency"


def test_law_used_comes_only_from_structured_request_header() -> None:
    record = parse_archived_request(
        """
        <h1>Request mentioning the Freedom of Information Act</h1>
        <p class="request-header__subtitle">
          Requester made this Government Information (Public Access) request to
          <a href="/body/nsw-agency">NSW Agency</a>
        </p>
        """,
        source_url="https://example.test/request/example",
        archive_url="https://web.archive.org/example",
        archive_timestamp="20200101000000",
    )
    assert record["law_used"] == "gipa"


def test_authority_extraction_deduplicates_public_body_selector_matches() -> None:
    record = parse_archived_request(
        """
        <a class="public-body" href="/body/agency">Agency</a>
        """,
        source_url="https://example.test/request/example",
        archive_url="https://web.archive.org/example",
        archive_timestamp="20200101000000",
    )
    assert record["authority_slug"] == "agency"


def test_law_used_recognizes_rti_and_foi_headers() -> None:
    for phrase, expected in (
        ("right to information", "rti"),
        ("freedom of information", "foi"),
    ):
        record = parse_archived_request(
            f'<p class="request-header__subtitle">Made this {phrase} request</p>',
            source_url="https://example.test/request/example",
            archive_url="https://web.archive.org/example",
            archive_timestamp="20200101000000",
        )
        assert record["law_used"] == expected


def test_missing_authority_uses_conservative_text_fallback() -> None:
    record = parse_archived_request(
        '<div class="request-authority">Fallback Authority</div>',
        source_url="https://example.test/request/example",
        archive_url="https://web.archive.org/example",
        archive_timestamp="20200101000000",
    )
    assert record["authority"] == "Fallback Authority"


def test_archive_replay_url_handles_empty_inputs() -> None:
    url = archive_replay_url("", "")
    assert url == "https://web.archive.org/web/id_/"


def test_archive_replay_url_raises_type_error_on_none() -> None:
    with pytest.raises(TypeError):
        # type: ignore is needed since we're intentionally passing an invalid type
        archive_replay_url(None, "20240101")  # type: ignore[arg-type]


def test_extract_date_handles_missing_tags() -> None:
    from bs4 import BeautifulSoup

    from fyi_archive.historical_core import _extract_date  # noqa: PLC2701

    soup = BeautifulSoup("<html></html>", "html.parser")
    assert _extract_date(soup, ("datePublished",)) is None


def test_first_text_handles_missing_tags() -> None:
    from bs4 import BeautifulSoup

    from fyi_archive.historical_core import _first_text  # noqa: PLC2701

    soup = BeautifulSoup("<html></html>", "html.parser")
    assert _first_text(soup, ("h1",)) == ""


def test_first_text_handles_empty_text() -> None:
    from bs4 import BeautifulSoup

    from fyi_archive.historical_core import _first_text  # noqa: PLC2701

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
    assert record["state_text"] == "open"
    assert record["state"] == ""
