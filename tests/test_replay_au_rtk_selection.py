from __future__ import annotations

import httpx
import pytest

from scripts.replay_au_rtk_selection import _assert_archive_url, _parse_json


def test_archive_url_boundary_rejects_origin() -> None:
    _assert_archive_url("https://web.archive.org/web/1id_/https://example.test")
    with pytest.raises(ValueError, match="escaped Internet Archive"):
        _assert_archive_url("https://www.righttoknow.org.au/request/example")


def test_json_parser_extracts_authority_without_following_links() -> None:
    raw = b'{"title":"T","state":"successful","public_body":{"name":"Agency","url_name":"agency","tags":["nsw"]}}'
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


def test_httpx_defaults_do_not_follow_redirects() -> None:
    with httpx.Client(follow_redirects=False) as client:
        assert client.follow_redirects is False
