from scripts.classify_au_rtk_replay import classify


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
