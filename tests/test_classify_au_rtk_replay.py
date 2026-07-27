import json

import pytest

from scripts import classify_au_rtk_replay as classifier
from scripts.classify_au_rtk_replay import classify, load_complete_replay


def test_classification_uses_explicit_tags_and_unanimous_authority_crosswalk() -> None:
    records = [
        {"authority_slug": "federal-body", "authority_tags": ["federal"], "law_used": ""},
        {"authority_slug": "nsw-body", "authority_tags": ["NSW"], "law_used": ""},
        {"authority_slug": "nsw-body", "authority_tags": [], "law_used": ""},
        {"authority_slug": "unknown", "authority_tags": [], "law_used": ""},
    ]
    result = classify(records)
    assert [record["jurisdiction"] for record in result] == [
        "AU-CTH",
        "AU-NSW",
        "AU-NSW",
        "UNRESOLVED",
    ]


def test_gipa_is_explicit_nsw_evidence_and_conflicts_abstain() -> None:
    records = [
        {"authority_slug": "body", "authority_tags": ["federal"], "law_used": "gipa"},
        {"authority_slug": "", "authority_tags": [], "law_used": "gipa"},
    ]
    result = classify(records)
    assert result[0]["jurisdiction"] == "UNRESOLVED"
    assert result[1]["jurisdiction"] == "AU-NSW"


def test_complete_replay_validation_fails_closed_on_partial_membership(
    tmp_path, monkeypatch
) -> None:
    selection = tmp_path / "selection.json"
    selection.write_text(
        json.dumps(
            {
                "record_count": 2,
                "records": [
                    {"canonical_slug": "one"},
                    {"canonical_slug": "two"},
                ],
            }
        )
    )
    records = tmp_path / "records"
    records.mkdir()
    (records / "one.json").write_text(
        json.dumps({"status": "captured", "parser_version": 2})
    )
    monkeypatch.setattr(classifier, "sha256_file", lambda _path: classifier.SELECTION_SHA256)
    monkeypatch.setattr(classifier, "EXPECTED_SLUGS", 2)
    with pytest.raises(ValueError, match="membership mismatch"):
        load_complete_replay(records, selection)


def test_complete_replay_validation_binds_selection_provenance(tmp_path, monkeypatch) -> None:
    selected = {
        "canonical_slug": "one",
        "source_url": "https://www.righttoknow.org.au/request/one.json",
        "archive_timestamp": "20200101000000",
        "archive_digest": "DIGEST",
        "media_kind": "json",
        "selection_reason": "latest_successful_json",
    }
    selection = tmp_path / "selection.json"
    selection.write_text(json.dumps({"record_count": 1, "records": [selected]}))
    records = tmp_path / "records"
    records.mkdir()
    (records / "one.json").write_text(
        json.dumps(
            {
                **selected,
                "status": "captured",
                "parser_version": 2,
                "archive_digest": "WRONG",
            }
        )
    )
    monkeypatch.setattr(classifier, "sha256_file", lambda _path: classifier.SELECTION_SHA256)
    monkeypatch.setattr(classifier, "EXPECTED_SLUGS", 1)
    with pytest.raises(ValueError, match="provenance mismatch"):
        load_complete_replay(records, selection)
