from __future__ import annotations

import json
from pathlib import Path

from fyi_archive.derived_layer import validate_derived_manifest

FIXTURE = Path("tests/fixtures/foi_o_extraction_contract_nz.json")


def test_pinned_candidate_contract_is_accepted() -> None:
    result = validate_derived_manifest(json.loads(FIXTURE.read_text(encoding="utf-8")))
    assert result["ok"] is True


def test_mutable_source_revision_is_rejected() -> None:
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    document["provenance"]["source_revision"] = "main"
    result = validate_derived_manifest(document)
    assert result["ok"] is False
    assert "immutable" in result["errors"][-1]


def test_missing_run_provenance_is_rejected() -> None:
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del document["provenance"]["extraction_run_id"]
    result = validate_derived_manifest(document)
    assert result["ok"] is False
    assert "extraction_run_id" in " ".join(result["errors"])
