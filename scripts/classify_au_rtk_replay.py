"""Classify completed AU RightToKnow replay records from explicit authority evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import jsonschema

from fyi_archive.jurisdictions import jurisdiction_for_body_tag, load_jurisdiction_rules
from scripts.prepare_au_rtk_replay_selection import APPROVED_CDX_SHA256, EXPECTED_SLUGS
from scripts.replay_au_rtk_selection import PARSER_VERSION, SELECTION_SHA256

PROFILE_MAP = {"FEDERAL": "AU-CTH", "NSW": "AU-NSW"}
SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "schemas"
    / "au-rtk-jurisdiction-classification-candidate.schema.json"
)
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


def load_complete_replay(
    records_dir: Path,
    raw_dir: Path,
    selection_path: Path,
) -> list[dict[str, Any]]:
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
    if selection.get("record_count") != EXPECTED_SLUGS or len(selected) != EXPECTED_SLUGS:
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
        if record.get("status") != "captured" or record.get("parser_version") != PARSER_VERSION:
            raise ValueError(
                f"replay is not complete parser-v{PARSER_VERSION} capture: {path.name}"
            )
        if any(record.get(field) != expected.get(field) for field in SELECTION_FIELDS):
            raise ValueError(f"replay selection provenance mismatch: {path.name}")
        suffix = ".json" if expected["media_kind"] == "json" else ".html"
        raw_path = raw_dir / f"{path.stem}{suffix}"
        if not raw_path.is_file():
            raise ValueError(f"replay raw content is missing: {raw_path.name}")
        raw_sha256 = sha256_file(raw_path)
        if (
            record.get("raw_sha256") != raw_sha256
            or record.get("byte_count") != raw_path.stat().st_size
        ):
            raise ValueError(f"replay raw integrity mismatch: {raw_path.name}")
        records.append(
            {
                "canonical_slug": path.stem,
                **record,
                "_record_sha256": sha256_file(path),
                "_record_byte_count": path.stat().st_size,
                "_raw_filename": raw_path.name,
            }
        )
    expected_raw_names = {record["_raw_filename"] for record in records}
    actual_raw_names = {path.name for path in raw_dir.iterdir() if path.is_file()}
    if actual_raw_names != expected_raw_names:
        missing = sorted(expected_raw_names - actual_raw_names)
        extra = sorted(actual_raw_names - expected_raw_names)
        raise ValueError(f"replay raw membership mismatch: missing={missing[:3]} extra={extra[:3]}")
    return records


def write_replay_index(records: list[dict[str, Any]], output_path: Path) -> dict[str, Any]:
    """Write a deterministic integrity index for the non-final replay candidate."""
    entries = []
    for record in records:
        entries.append(
            {
                "canonical_slug": record["canonical_slug"],
                "media_kind": record["media_kind"],
                "source_url": record["source_url"],
                "archive_timestamp": record["archive_timestamp"],
                "archive_digest": record["archive_digest"],
                "raw_filename": record["_raw_filename"],
                "raw_byte_count": record["byte_count"],
                "raw_sha256": record["raw_sha256"],
                "record_filename": f"{record['canonical_slug']}.json",
                "record_byte_count": record["_record_byte_count"],
                "record_sha256": record["_record_sha256"],
            }
        )
    output_path.write_text(
        "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in entries),
        encoding="utf-8",
    )
    return {
        "path": output_path.name,
        "record_count": len(entries),
        "byte_count": output_path.stat().st_size,
        "sha256": sha256_file(output_path),
    }


def validate_candidate_summary(summary: dict[str, Any]) -> None:
    """Validate schema and cross-field count invariants for the candidate packet."""
    jsonschema.validate(
        summary,
        json.loads(SCHEMA_PATH.read_text(encoding="utf-8")),
    )
    counts = summary["counts"]
    outputs = summary["jurisdiction_outputs"]
    if sum(counts.values()) != summary["captured_record_count"]:
        raise ValueError("jurisdiction counts do not cover the captured replay")
    for jurisdiction, count in counts.items():
        if outputs[jurisdiction]["record_count"] != count:
            raise ValueError(f"{jurisdiction} output count does not match classification count")
    if summary["replay_index"]["record_count"] != summary["captured_record_count"]:
        raise ValueError("replay index count does not match captured replay")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-dir", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    records = load_complete_replay(args.records_dir, args.raw_dir, args.selection)
    classified = classify(records)
    args.output_root.mkdir(parents=True, exist_ok=True)
    replay_index = write_replay_index(
        records,
        args.output_root / "replay-index.candidate.jsonl",
    )
    paths = {
        "AU-CTH": args.output_root / "au-cth.candidate.jsonl",
        "AU-NSW": args.output_root / "au-nsw.candidate.jsonl",
        "UNRESOLVED": args.output_root / "unresolved.candidate.jsonl",
    }
    counts = {}
    hashes = {}
    for jurisdiction, path in paths.items():
        selected = [
            {key: value for key, value in record.items() if not key.startswith("_")}
            for record in classified
            if record["jurisdiction"] == jurisdiction
        ]
        path.write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in selected),
            encoding="utf-8",
        )
        counts[jurisdiction] = len(selected)
        hashes[jurisdiction] = {
            "path": path.name,
            "record_count": len(selected),
            "byte_count": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    summary = {
        "schema": "fyi-archive.au-rtk-jurisdiction-classification-candidate.v1",
        "status": "candidate_non_final",
        "source_cdx_sha256": APPROVED_CDX_SHA256,
        "selection_sha256": SELECTION_SHA256,
        "captured_record_count": len(records),
        "counts": counts,
        "replay_index": replay_index,
        "jurisdiction_outputs": hashes,
        "publication": False,
        "redistribution": False,
        "manifest_finalization_authorized": False,
    }
    validate_candidate_summary(summary)
    (args.output_root / "classification-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
