import json
from hashlib import sha256

import jsonschema
import pytest

from scripts import classify_au_rtk_replay as classifier
from scripts.classify_au_rtk_replay import classify, load_complete_replay, write_replay_index


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
    raw = tmp_path / "raw"
    raw.mkdir()
    (records / "one.json").write_text(json.dumps({"status": "captured", "parser_version": 2}))
    monkeypatch.setattr(classifier, "sha256_file", lambda _path: classifier.SELECTION_SHA256)
    monkeypatch.setattr(classifier, "EXPECTED_SLUGS", 2)
    with pytest.raises(ValueError, match="membership mismatch"):
        load_complete_replay(records, raw, selection)


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
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "one.json").write_bytes(b"raw")
    (records / "one.json").write_text(
        json.dumps(
            {
                **selected,
                "status": "captured",
                "parser_version": classifier.PARSER_VERSION,
                "archive_digest": "WRONG",
            }
        )
    )
    monkeypatch.setattr(classifier, "sha256_file", lambda _path: classifier.SELECTION_SHA256)
    monkeypatch.setattr(classifier, "EXPECTED_SLUGS", 1)
    with pytest.raises(ValueError, match="provenance mismatch"):
        load_complete_replay(records, raw, selection)


def test_complete_replay_and_index_bind_raw_and_record_hashes(tmp_path, monkeypatch) -> None:
    raw_bytes = b'{"title":"example"}'
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
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "one.json").write_bytes(raw_bytes)
    records_dir = tmp_path / "records"
    records_dir.mkdir()
    record_path = records_dir / "one.json"
    record_path.write_text(
        json.dumps(
            {
                **selected,
                "status": "captured",
                "parser_version": classifier.PARSER_VERSION,
                "raw_sha256": sha256(raw_bytes).hexdigest(),
                "byte_count": len(raw_bytes),
            }
        )
    )
    monkeypatch.setattr(classifier, "sha256_file", classifier.sha256_file)
    monkeypatch.setattr(classifier, "SELECTION_SHA256", classifier.sha256_file(selection))
    monkeypatch.setattr(classifier, "EXPECTED_SLUGS", 1)
    records = load_complete_replay(records_dir, raw, selection)
    index_path = tmp_path / "index.jsonl"
    index = write_replay_index(records, index_path)
    entry = json.loads(index_path.read_text())
    assert index["record_count"] == 1
    assert entry["raw_sha256"] == sha256(raw_bytes).hexdigest()
    assert entry["record_sha256"] == classifier.sha256_file(record_path)


def test_candidate_schema_requires_complete_bounded_non_final_packet() -> None:
    artifact = {
        "path": "candidate.jsonl",
        "record_count": 0,
        "byte_count": 0,
        "sha256": "a" * 64,
    }
    candidate = {
        "schema": "fyi-archive.au-rtk-jurisdiction-classification-candidate.v1",
        "status": "candidate_non_final",
        "source_cdx_sha256": classifier.APPROVED_CDX_SHA256,
        "selection_sha256": classifier.SELECTION_SHA256,
        "captured_record_count": classifier.EXPECTED_SLUGS,
        "counts": {"AU-CTH": 0, "AU-NSW": 0, "UNRESOLVED": classifier.EXPECTED_SLUGS},
        "replay_index": {**artifact, "record_count": classifier.EXPECTED_SLUGS},
        "jurisdiction_outputs": {
            "AU-CTH": artifact,
            "AU-NSW": artifact,
            "UNRESOLVED": {**artifact, "record_count": classifier.EXPECTED_SLUGS},
        },
        "publication": False,
        "redistribution": False,
        "manifest_finalization_authorized": False,
    }
    classifier.validate_candidate_summary(candidate)
    candidate["counts"]["UNRESOLVED"] -= 1
    with pytest.raises(ValueError, match="do not cover"):
        classifier.validate_candidate_summary(candidate)
    candidate["counts"]["UNRESOLVED"] += 1
    candidate["manifest_finalization_authorized"] = True
    with pytest.raises(jsonschema.ValidationError):
        classifier.validate_candidate_summary(candidate)
