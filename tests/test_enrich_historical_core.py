from __future__ import annotations

from pathlib import Path

from scripts.enrich_historical_core import enrich


def test_enrichment_retries_a_bounded_offset_slice() -> None:
    html = Path("tests/fixtures/alaveteli_request.html").read_bytes()
    calls: list[str] = []

    def fetch(replay_url: str, _user_agent: str, _timeout_seconds: float) -> bytes:
        calls.append(replay_url)
        if len(calls) == 1:
            raise TimeoutError("transient timeout")
        return html

    result = enrich(
        {
            "records": [
                {"source_url": "https://example.test/request/ignored", "observed_at": "20240101"},
                {
                    "source_url": "https://example.test/request/road-safety",
                    "observed_at": "20240101",
                    "archive_digest": "sha1:fixture",
                },
            ]
        },
        instance_id="example",
        limit=1,
        start_offset=1,
        retries=1,
        retry_delay_seconds=0,
        delay_seconds=0,
        user_agent="test-agent",
        timeout_seconds=1,
        fetch_replay=fetch,
    )

    assert result["input_record_count"] == 2
    assert result["start_offset"] == 1
    assert result["processed_record_count"] == 1
    assert result["extracted_record_count"] == 1
    assert len(calls) == 2
    assert result["records"][0]["attempt_count"] == 2
    assert result["records"][0]["source_url"].endswith("/road-safety")
