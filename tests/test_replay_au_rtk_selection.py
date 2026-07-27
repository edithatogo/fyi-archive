from __future__ import annotations

import json

import httpx
import pytest

from scripts import replay_au_rtk_selection as replay
from scripts.replay_au_rtk_selection import _assert_archive_url, _parse_json, record_from_raw


def test_archive_url_boundary_rejects_origin() -> None:
    _assert_archive_url("https://web.archive.org/web/1id_/https://example.test")
    with pytest.raises(ValueError, match="escaped Internet Archive"):
        _assert_archive_url("https://www.righttoknow.org.au/request/example")


def test_json_parser_extracts_authority_without_following_links() -> None:
    raw = b'{"id":7,"title":"T","law_used":"gipa","created_at":"2020-01-01","updated_at":"2020-01-02","state":"successful","public_body":{"name":"Agency","url_name":"agency","tags":[["nsw",null]]}}'
    selected = {
        "source_url": "https://www.righttoknow.org.au/request/example.json",
        "archive_timestamp": "20200101",
        "archive_digest": "ABC",
        "canonical_slug": "example",
    }
    result = _parse_json(raw, selected=selected, replay_url="https://web.archive.org/example")
    assert result["authority"] == "Agency"
    assert result["authority_slug"] == "agency"
    assert result["authority_tags"] == ["nsw"]
    assert result["law_used"] == "gipa"
    assert result["first_seen"] == "2020-01-01"
    assert result["request_id"] == 7


def test_httpx_defaults_do_not_follow_redirects() -> None:
    with httpx.Client(follow_redirects=False) as client:
        assert client.follow_redirects is False


def test_existing_raw_json_is_reparsed_without_network() -> None:
    selected = {
        "source_url": "https://www.righttoknow.org.au/request/example.json",
        "archive_timestamp": "20200101",
        "archive_digest": "ABC",
        "canonical_slug": "example",
        "media_kind": "json",
        "selection_reason": "latest_successful_json",
    }
    result = record_from_raw(
        selected,
        b'{"title":"T","public_body":{"tags":[["federal",null]]}}',
        replay_url="https://web.archive.org/example",
        content_type="application/json",
    )
    assert result["status"] == "captured"
    assert result["parser_version"] == replay.PARSER_VERSION
    assert result["authority_tags"] == ["federal"]


def test_html_request_key_uses_canonical_slug_not_tracking_query() -> None:
    selected = {
        "source_url": "https://www.righttoknow.org.au/request/example?utm_source=right-to-know",
        "archive_timestamp": "20200101",
        "archive_digest": "ABC",
        "canonical_slug": "example",
        "media_kind": "html",
        "selection_reason": "latest_successful_primary_html_fallback",
    }
    result = record_from_raw(
        selected,
        b"<html><h1>Example</h1><a href='/body/agency'>Agency</a></html>",
        replay_url="https://web.archive.org/example",
        content_type="text/html",
    )
    assert result["request_key"] == "example"
    assert result["authority"] == "Agency"
    assert result["authority_slug"] == "agency"


def test_sequential_mode_opens_circuit_after_bounded_failures(tmp_path, monkeypatch) -> None:
    records = [
        {
            "canonical_slug": str(index),
            "source_url": f"https://www.righttoknow.org.au/request/{index}",
            "archive_timestamp": "20200101",
            "archive_digest": "ABC",
            "media_kind": "html",
            "selection_reason": "latest_successful_primary_html_fallback",
        }
        for index in range(2_082)
    ]
    selection = tmp_path / "selection.json"
    selection.write_text(json.dumps({"record_count": 2_082, "records": records}))
    monkeypatch.setattr(replay, "sha256_file", lambda _path: replay.SELECTION_SHA256)
    monkeypatch.setattr(
        replay,
        "replay_one",
        lambda selected, **_kwargs: {
            **selected,
            "status": "fetch_failed",
            "extraction_status": "fetch_failed",
        },
    )
    result = replay.run(
        selection,
        output_root=tmp_path / "output",
        workers=1,
        launch_delay_seconds=0,
        timeout_seconds=1,
        retries=0,
        circuit_breaker_failures=3,
    )
    assert result["circuit_open"] is True
    assert result["record_count"] == 3
    assert result["pending_count"] == 2_079
