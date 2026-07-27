"""Classify completed AU RightToKnow replay records from explicit authority evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from fyi_archive.jurisdictions import jurisdiction_for_body_tag, load_jurisdiction_rules
from scripts.prepare_au_rtk_replay_selection import EXPECTED_SLUGS
from scripts.replay_au_rtk_selection import SELECTION_SHA256

PROFILE_MAP = {"FEDERAL": "AU-CTH", "NSW": "AU-NSW"}
SELECTION_FIELDS = (
    "source_url",
    "archive_timestamp",
    "archive_digest",
    "media_kind",
    "selection_reason",
)


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


def load_complete_replay(records_dir: Path, selection_path: Path) -> list[dict[str, Any]]:
    """Load replay records only when they exactly cover the authorized selection."""
    selection_digest = sha256_file(selection_path)
    if selection_digest != SELECTION_SHA256:
        raise ValueError(f"selection SHA-256 mismatch: {selection_digest}")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    selected = {
        str(item["canonical_slug"]): item
        for item in selection.get("records", [])
        if isinstance(item, dict) and item.get("canonical_slug")
    }
    if (
        selection.get("record_count") != EXPECTED_SLUGS
        or len(selected) != EXPECTED_SLUGS
    ):
        raise ValueError("authorized selection membership/count mismatch")

    paths = sorted(records_dir.glob("*.json"))
    actual_slugs = {path.stem for path in paths}
    if len(paths) != EXPECTED_SLUGS or actual_slugs != set(selected):
        missing = sorted(set(selected) - actual_slugs)
        extra = sorted(actual_slugs - set(selected))
        raise ValueError(
            f"replay membership mismatch: records={len(paths)} "
            f"missing={missing[:3]} extra={extra[:3]}"
        )

    records = []
    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        expected = selected[path.stem]
        if record.get("status") != "captured" or record.get("parser_version") != 2:
            raise ValueError(f"replay is not complete parser-v2 capture: {path.name}")
        if any(record.get(field) != expected.get(field) for field in SELECTION_FIELDS):
            raise ValueError(f"replay selection provenance mismatch: {path.name}")
        records.append({"canonical_slug": path.stem, **record})
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-dir", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    records = load_complete_replay(args.records_dir, args.selection)
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
        "selection_sha256": SELECTION_SHA256,
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
