from scripts.build_reconciled_backfill_queue import build_queue


def test_build_queue_requires_complete_retrieval_and_sorts_slugs() -> None:
    index = {
        "records": [
            {"source_url": "https://www.fyi.org.nz/request/zeta"},
            {"source_url": "https://www.fyi.org.nz/request/alpha"},
            {"source_url": "https://www.fyi.org.nz/request/alpha"},
            {"source_url": "https://www.fyi.org.nz/request/alpha/response/1"},
        ]
    }
    retrieval = {"retrieval_status": "complete", "pagination_complete": True}
    assert build_queue(index, retrieval) == [
        {
            "request_id": "alpha",
            "url_title": "alpha",
            "source_url": "https://www.fyi.org.nz/request/alpha",
        },
        {
            "request_id": "zeta",
            "url_title": "zeta",
            "source_url": "https://www.fyi.org.nz/request/zeta",
        },
    ]


def test_build_queue_rejects_incomplete_retrieval() -> None:
    try:
        build_queue({"records": []}, {"retrieval_status": "failed", "pagination_complete": False})
    except ValueError as error:
        assert "incomplete" in str(error)
    else:
        raise AssertionError("incomplete retrieval must fail closed")
