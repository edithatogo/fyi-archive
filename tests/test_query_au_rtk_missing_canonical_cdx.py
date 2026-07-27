import json

from scripts import query_au_rtk_missing_canonical_cdx as completion
from scripts.query_au_rtk_missing_canonical_cdx import CDX_ENDPOINT


def test_completion_endpoint_is_internet_archive_only() -> None:
    assert CDX_ENDPOINT == "https://web.archive.org/cdx/search/cdx"


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
