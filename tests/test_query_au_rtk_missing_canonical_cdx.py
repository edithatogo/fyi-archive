import hashlib
import json

import httpx
import pytest

from scripts import query_au_rtk_missing_canonical_cdx as completion
from scripts.query_au_rtk_missing_canonical_cdx import CDX_ENDPOINT


def test_completion_endpoint_is_internet_archive_only() -> None:
    assert CDX_ENDPOINT == "https://web.archive.org/cdx/search/cdx"


def test_response_rows_are_bound_to_exact_authorized_canonical_url() -> None:
    query = {
        "canonical_slug": "example",
        "media_kind": "json",
        "exact_url": "https://www.righttoknow.org.au/request/example.json",
    }
    records = completion.validate_response_rows(
        query,
        [
            completion.HEADER,
            [
                "http://www.righttoknow.org.au/request/example.json",
                "20200101000000",
                "DIGEST",
                "200",
                "123",
            ],
        ],
    )
    assert len(records) == 1


def test_response_rows_reject_population_expansion() -> None:
    query = {
        "canonical_slug": "example",
        "media_kind": "html",
        "exact_url": "https://www.righttoknow.org.au/request/example",
    }
    with pytest.raises(ValueError, match="escaped"):
        completion.validate_response_rows(
            query,
            [
                completion.HEADER,
                [
                    "https://www.righttoknow.org.au/request/example/response/1",
                    "20200101000000",
                    "DIGEST",
                    "200",
                    "123",
                ],
            ],
        )


def test_complete_checkpoint_must_match_query_and_cdx_provenance(tmp_path) -> None:
    query = {
        "canonical_slug": "example",
        "media_kind": "html",
        "exact_url": "https://www.righttoknow.org.au/request/example",
    }
    body = json.dumps([completion.HEADER]).encode()
    body_dir = tmp_path / "response-bodies"
    body_dir.mkdir()
    (body_dir / "example.html.json").write_bytes(body)
    checkpoint = {
        **query,
        "status": "complete",
        "record_count": 0,
        "records": [],
        "request_url": (
            "https://web.archive.org/cdx/search/cdx"
            "?url=https%3A%2F%2Fwww.righttoknow.org.au%2Frequest%2Fexample"
        ),
        "response_body_filename": "example.html.json",
        "response_byte_count": len(body),
        "response_sha256": hashlib.sha256(body).hexdigest(),
    }
    assert completion.valid_complete_checkpoint(query, checkpoint, output_root=tmp_path) is True
    checkpoint["exact_url"] = "https://www.righttoknow.org.au/request/other"
    assert completion.valid_complete_checkpoint(query, checkpoint, output_root=tmp_path) is False


def test_complete_checkpoint_rejects_non_cdx_request_url(tmp_path) -> None:
    query = {
        "canonical_slug": "example",
        "media_kind": "html",
        "exact_url": "https://www.righttoknow.org.au/request/example",
    }
    body = json.dumps([completion.HEADER]).encode()
    body_dir = tmp_path / "response-bodies"
    body_dir.mkdir()
    (body_dir / "example.html.json").write_bytes(body)
    checkpoint = {
        **query,
        "status": "complete",
        "record_count": 0,
        "records": [],
        "request_url": "https://www.righttoknow.org.au/request/example",
        "response_body_filename": "example.html.json",
        "response_byte_count": len(body),
        "response_sha256": hashlib.sha256(body).hexdigest(),
    }
    assert completion.valid_complete_checkpoint(query, checkpoint, output_root=tmp_path) is False


def test_complete_checkpoint_rejects_changed_response_body(tmp_path) -> None:
    query = {
        "canonical_slug": "example",
        "media_kind": "html",
        "exact_url": "https://www.righttoknow.org.au/request/example",
    }
    original = json.dumps([completion.HEADER]).encode()
    body_dir = tmp_path / "response-bodies"
    body_dir.mkdir()
    body_path = body_dir / "example.html.json"
    body_path.write_bytes(original)
    checkpoint = {
        **query,
        "status": "complete",
        "record_count": 0,
        "records": [],
        "request_url": "https://web.archive.org/cdx/search/cdx?url=example",
        "response_body_filename": body_path.name,
        "response_byte_count": len(original),
        "response_sha256": hashlib.sha256(original).hexdigest(),
    }
    body_path.write_bytes(b"[]")
    assert completion.valid_complete_checkpoint(query, checkpoint, output_root=tmp_path) is False


def test_completion_replay_selection_prefers_latest_json_and_remains_unauthorized() -> None:
    results = []
    for index in range(completion.EXPECTED_MISSING_SLUGS):
        slug = f"slug-{index}"
        for media_kind in ("json", "html"):
            records = []
            if index == 0:
                suffix = ".json" if media_kind == "json" else ""
                records = [
                    [
                        f"https://www.righttoknow.org.au/request/{slug}{suffix}",
                        "20200101000000",
                        f"{media_kind}-old",
                        "200",
                        "1",
                    ],
                    [
                        f"https://www.righttoknow.org.au/request/{slug}{suffix}",
                        "20210101000000",
                        f"{media_kind}-new",
                        "200",
                        "2",
                    ],
                ]
            results.append(
                {
                    "canonical_slug": slug,
                    "media_kind": media_kind,
                    "exact_url": (
                        f"https://www.righttoknow.org.au/request/{slug}"
                        f"{'.json' if media_kind == 'json' else ''}"
                    ),
                    "status": "complete",
                    "records": records,
                }
            )
    candidate = {
        "failed_query_count": 0,
        "pending_query_count": 0,
        "results": results,
    }
    selection = completion.build_completion_replay_selection(
        candidate,
        completion_candidate_sha256="a" * 64,
    )
    assert selection["queried_slug_count"] == completion.EXPECTED_MISSING_SLUGS
    assert selection["selected_slug_count"] == 1
    assert selection["json_count"] == 1
    assert selection["html_fallback_count"] == 0
    assert selection["records"][0]["archive_digest"] == "json-new"
    assert selection["no_capture_slug_count"] == completion.EXPECTED_MISSING_SLUGS - 1
    assert selection["replay_authorized"] is False
    assert selection["manifest_finalization_authorized"] is False
    completion.validate_completion_replay_selection(selection)
    selection["records"][0]["source_url"] += "?expanded=true"
    with pytest.raises(ValueError, match="escaped its exact canonical URL"):
        completion.validate_completion_replay_selection(selection)


def test_sequential_completion_opens_circuit(tmp_path, monkeypatch) -> None:
    queries = [
        {
            "canonical_slug": str(index),
            "media_kind": "json",
            "exact_url": f"https://www.righttoknow.org.au/request/{index}.json",
        }
        for index in range(completion.EXPECTED_QUERY_COUNT)
    ]
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"query_count": len(queries), "queries": queries}))
    monkeypatch.setattr(
        completion,
        "query_one",
        lambda query, **_kwargs: {**query, "status": "failed", "records": []},
    )
    result = completion.run(
        plan,
        output_root=tmp_path / "output",
        workers=1,
        launch_delay_seconds=0,
        timeout_seconds=1,
        retries=0,
        circuit_breaker_failures=4,
    )
    assert result["circuit_open"] is True
    assert result["query_count"] == 4
    assert result["pending_query_count"] == completion.EXPECTED_QUERY_COUNT - 4


def test_sequential_completion_reuses_one_http_client(tmp_path, monkeypatch) -> None:
    queries = [
        {
            "canonical_slug": str(index),
            "media_kind": media_kind,
            "exact_url": (
                f"https://www.righttoknow.org.au/request/{index}"
                f"{'.json' if media_kind == 'json' else ''}"
            ),
        }
        for index in range(completion.EXPECTED_MISSING_SLUGS)
        for media_kind in ("json", "html")
    ]
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"query_count": len(queries), "queries": queries}))
    observed_clients: list[httpx.Client] = []

    def successful_query(query, *, client, **_kwargs):
        observed_clients.append(client)
        return {**query, "status": "complete", "records": []}

    monkeypatch.setattr(completion, "query_one", successful_query)
    result = completion.run(
        plan,
        output_root=tmp_path / "output",
        workers=1,
        launch_delay_seconds=0,
        timeout_seconds=1,
        retries=0,
        circuit_breaker_failures=4,
    )
    assert result["complete_query_count"] == completion.EXPECTED_QUERY_COUNT
    assert len({id(client) for client in observed_clients}) == 1
