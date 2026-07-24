from __future__ import annotations

import json
from pathlib import Path

import pytest

from fyi_archive.au_corpus_readiness import load_sampling_frame, validate_sampling_frame

FRAME = Path("configs/au/corpus_sampling_frame.json")


def test_committed_au_sampling_frame_is_bounded_and_fail_closed() -> None:
    document = load_sampling_frame(FRAME)
    assert document["capture_authorized"] is False
    assert document["publication_authorized"] is False
    assert [item["jurisdiction"] for item in document["strata"]] == ["FEDERAL", "NSW"]
    assert all(item["request_cap"] <= 25 for item in document["strata"])


def test_sampling_frame_rejects_implicit_unknowns_and_authorization() -> None:
    document = json.loads(FRAME.read_text(encoding="utf-8"))
    document["capture_authorized"] = True
    document["strata"][0]["outcomes"] = ["guessed"]
    result = validate_sampling_frame(document)
    assert result["ok"] is False
    assert "capture_authorized" in " ".join(result["errors"])
    assert "unknown outcomes" in " ".join(result["errors"])


def test_sampling_frame_reports_structural_and_rights_errors(tmp_path: Path) -> None:
    result = validate_sampling_frame({
        "schema": "wrong",
        "capture_authorized": False,
        "publication_authorized": True,
        "strata": [
            "not-an-object",
            {
                "jurisdiction": "MARS",
                "outcomes": [],
                "request_cap": 0,
            },
            {
                "jurisdiction": "NSW",
                "outcomes": ["unknown"],
                "request_cap": 1,
            },
            {
                "jurisdiction": "NSW",
                "outcomes": ["unknown"],
                "request_cap": 1,
            },
        ],
        "rights_gates": {},
    })
    errors = " ".join(result["errors"])
    assert result["ok"] is False
    assert "unsupported" in errors
    assert "publication_authorized" in errors
    assert "must be an object" in errors
    assert "unknown jurisdiction" in errors
    assert "duplicate jurisdiction" in errors
    assert "must be non-empty" in errors
    assert "request_cap" in errors
    assert "rights_gates are incomplete" in errors
    assert "FEDERAL" in errors

    path = tmp_path / "frame.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        load_sampling_frame(path)


def test_sampling_frame_requires_strata_and_rights_object() -> None:
    result = validate_sampling_frame({
        "schema": "fyi-archive.au-sampling-frame.v1",
        "capture_authorized": False,
        "publication_authorized": False,
        "strata": None,
        "rights_gates": None,
    })
    assert result["ok"] is False
    assert "strata must" in " ".join(result["errors"])
    assert "rights_gates must" in " ".join(result["errors"])
