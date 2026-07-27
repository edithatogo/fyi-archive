"""Classify completed AU RightToKnow replay records from explicit authority evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from fyi_archive.jurisdictions import jurisdiction_for_body_tag, load_jurisdiction_rules

PROFILE_MAP = {"FEDERAL": "AU-CTH", "NSW": "AU-NSW"}


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _direct_profile(record: dict[str, Any], rules: dict[str, Any]) -> str | None:
    profiles = {
        PROFILE_MAP[jurisdiction]
        for tag in record.get("authority_tags") or []
        if (jurisdiction := jurisdiction_for_body_tag(str(tag), rules)) in PROFILE_MAP
    }
    if str(record.get("law_used") or "").lower() == "gipa":
        profiles.add("AU-NSW")
    return next(iter(profiles)) if len(profiles) == 1 else None


def classify(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Classify by explicit tags, then propagate only unanimous authority evidence."""
    rules = load_jurisdiction_rules()
    authority_profiles: dict[str, set[str]] = defaultdict(set)
    for record in records:
        profile = _direct_profile(record, rules)
        authority_slug = str(record.get("authority_slug") or "")
        if profile and authority_slug:
            authority_profiles[authority_slug].add(profile)

    output = []
    for record in records:
        direct = _direct_profile(record, rules)
        authority_slug = str(record.get("authority_slug") or "")
        propagated = authority_profiles.get(authority_slug, set()) if authority_slug else set()
        if direct:
            jurisdiction = direct
            basis = "explicit_authority_tag_or_regime"
        elif len(propagated) == 1:
            jurisdiction = next(iter(propagated))
            basis = "unanimous_authority_slug_cross_record_evidence"
        else:
            jurisdiction = "UNRESOLVED"
            basis = "insufficient_or_conflicting_authority_evidence"
        output.append(
            {
                **record,
                "jurisdiction": jurisdiction,
                "jurisdiction_basis": basis,
            }
        )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-dir", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    records = []
    for path in sorted(args.records_dir.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("status") == "captured":
            records.append(record)
    classified = classify(records)
    args.output_root.mkdir(parents=True, exist_ok=True)
    paths = {
        "AU-CTH": args.output_root / "au-cth.candidate.jsonl",
        "AU-NSW": args.output_root / "au-nsw.candidate.jsonl",
        "UNRESOLVED": args.output_root / "unresolved.candidate.jsonl",
    }
    counts = {}
    hashes = {}
    for jurisdiction, path in paths.items():
        selected = [record for record in classified if record["jurisdiction"] == jurisdiction]
        path.write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in selected),
            encoding="utf-8",
        )
        counts[jurisdiction] = len(selected)
        hashes[jurisdiction] = sha256_file(path)
    summary = {
        "schema": "fyi-archive.au-rtk-jurisdiction-classification-candidate.v1",
        "status": "candidate_non_final",
        "captured_record_count": len(records),
        "counts": counts,
        "sha256": hashes,
        "publication": False,
        "redistribution": False,
        "manifest_finalization_authorized": False,
    }
    (args.output_root / "classification-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
