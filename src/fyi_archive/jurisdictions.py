"""Jurisdiction taxonomy helpers for multi-instance manifests."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DEFAULT_AU_RULES_PATH = Path(__file__).parents[2] / "configs" / "au" / "jurisdiction_rules.json"


def load_jurisdiction_rules(path: Path = DEFAULT_AU_RULES_PATH) -> dict[str, Any]:
    """Load and validate the committed AU jurisdiction rules."""
    document = json.loads(path.read_text(encoding="utf-8"))
    jurisdictions = document.get("jurisdictions")
    default = document.get("default")
    if not isinstance(jurisdictions, dict) or not isinstance(default, str):
        raise ValueError("Jurisdiction rules require jurisdictions and default")
    if default not in jurisdictions:
        raise ValueError(f"Jurisdiction rules default is not defined: {default}")
    if any(not isinstance(tags, list) for tags in jurisdictions.values()):
        raise ValueError("Jurisdiction rule values must be arrays")
    return document


def normalize_body_tag(tag: str) -> str:
    """Normalize a source body tag for deterministic rule matching."""
    return re.sub(r"[^a-z0-9]+", " ", tag.casefold()).strip()


def jurisdiction_for_body_tag(tag: str, rules: dict[str, Any] | None = None) -> str:
    """Resolve a body tag to an AU jurisdiction, falling back to ``OTHER``."""
    document = rules or load_jurisdiction_rules()
    normalized = normalize_body_tag(tag)
    for jurisdiction, tags in document["jurisdictions"].items():
        if normalized in {normalize_body_tag(str(candidate)) for candidate in tags}:
            return str(jurisdiction)
    return str(document["default"])


def authority_manifest_for_au(
    records: list[dict[str, Any]], rules: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build an AU authority manifest with deterministic jurisdiction labels."""
    authorities: dict[str, str] = {}
    for record in records:
        authority = str(record.get("authority") or "").strip()
        if not authority:
            continue
        body_tag = str(record.get("body_tag") or authority)
        jurisdiction = jurisdiction_for_body_tag(body_tag, rules)
        previous = authorities.get(authority)
        if previous is None or previous == "OTHER":
            authorities[authority] = jurisdiction
    return {
        "instance_id": "au-rtk",
        "authorities": [
            {"name": name, "jurisdiction": authorities[name]} for name in sorted(authorities)
        ],
    }
