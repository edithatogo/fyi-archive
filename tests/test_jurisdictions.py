"""Tests for AU body-tag jurisdiction taxonomy."""

from __future__ import annotations

import json
from pathlib import Path

from fyi_archive.jurisdictions import (
    authority_manifest_for_au,
    jurisdiction_for_body_tag,
    load_jurisdiction_rules,
)

ROOT = Path(__file__).parents[1]


def test_fixture_tags_resolve_to_expected_jurisdictions() -> None:
    rules = load_jurisdiction_rules()
    fixtures = json.loads(
        (ROOT / "tests" / "fixtures" / "au_jurisdiction_tags.json").read_text(encoding="utf-8")
    )

    assert all(
        jurisdiction_for_body_tag(fixture["tag"], rules) == fixture["jurisdiction"]
        for fixture in fixtures
    )


def test_unknown_body_tag_falls_back_to_other() -> None:
    assert jurisdiction_for_body_tag("agency-without-a-state") == "OTHER"


def test_au_authority_manifest_preserves_specific_classification() -> None:
    manifest = authority_manifest_for_au([
        {"authority": "Service NSW", "body_tag": "nsw"},
        {"authority": "Service NSW", "body_tag": "not-yet-classified"},
        {"authority": "Unknown agency", "body_tag": "unknown"},
    ])

    assert manifest == {
        "instance_id": "au-rtk",
        "authorities": [
            {"name": "Service NSW", "jurisdiction": "NSW"},
            {"name": "Unknown agency", "jurisdiction": "OTHER"},
        ],
    }
