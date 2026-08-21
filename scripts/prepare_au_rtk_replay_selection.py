"""Build the exact authorized AU RightToKnow replay selection from CDX metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

HEADER = ["original", "timestamp", "digest", "statuscode", "length"]
APPROVED_CDX_SHA256 = "954b0f80ad2a44038f364d240cc9baac815f252a43535c8403dec060ddb730bd"
EXPECTED_SLUGS = 2_082
EXPECTED_JSON = 1_225
EXPECTED_HTML = 857


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _candidate(row: list[str]) -> dict[str, str] | None:
    if len(row) != len(HEADER) or row[3] != "200":
        return None
    parsed = urlsplit(row[0])
    if (
        parsed.scheme not in {"http", "https"}
        or (parsed.hostname or "").lower() != "www.righttoknow.org.au"
    ):
        return None
    parts = parsed.path.split("/")
    if len(parts) != 3 or parts[:2] != ["", "request"] or not parts[2]:
        return None
    leaf = parts[2]
    media_kind = "json" if leaf.endswith(".json") else "html"
    slug = leaf[:-5] if media_kind == "json" else leaf
    if not slug or "." in slug:
        return None
    return {
        "canonical_slug": slug,
        "media_kind": media_kind,
        "source_url": row[0],
        "archive_timestamp": row[1],
        "archive_digest": row[2],
        "statuscode": row[3],
        "length": row[4],
    }


def build_selection(rows: list[Any], *, cdx_sha256: str) -> dict[str, Any]:
    """Choose latest JSON per slug, falling back to latest primary HTML."""
    if not rows or rows[0] != HEADER:
        raise ValueError("CDX header mismatch")
    by_slug: dict[str, dict[str, dict[str, str]]] = {}
    for raw_row in rows[1:]:
        if (
            not isinstance(raw_row, list)
            or len(raw_row) != len(HEADER)
            or not all(isinstance(value, str) for value in raw_row)
        ):
            raise ValueError("CDX row is malformed")
        candidate = _candidate(raw_row)
        if candidate is None:
            continue
        slug = candidate["canonical_slug"]
        kind = candidate["media_kind"]
        current = by_slug.setdefault(slug, {}).get(kind)
        if current is None or candidate["archive_timestamp"] > current["archive_timestamp"]:
            by_slug[slug][kind] = candidate

    selected = []
    for slug in sorted(by_slug):
        choices = by_slug[slug]
        record = choices.get("json") or choices.get("html")
        if record is None:
            raise ValueError(f"no replay candidate for {slug}")
        selected.append(
            {
                **record,
                "selection_reason": (
                    "latest_successful_json"
                    if record["media_kind"] == "json"
                    else "latest_successful_primary_html_fallback"
                ),
            }
        )
    json_count = sum(record["media_kind"] == "json" for record in selected)
    html_count = len(selected) - json_count
    return {
        "schema": "fyi-archive.au-rtk-replay-selection.v1",
        "status": "authorized_selection",
        "source_cdx_sha256": cdx_sha256,
        "selection_rule": "latest successful .json per canonical slug; otherwise latest successful primary HTML",
        "record_count": len(selected),
        "json_count": json_count,
        "html_fallback_count": html_count,
        "records": selected,
    }


def validate_authorized_counts(selection: dict[str, Any]) -> None:
    """Fail closed unless the derived population matches the exact authorization."""
    actual = (
        selection.get("record_count"),
        selection.get("json_count"),
        selection.get("html_fallback_count"),
    )
    expected = (EXPECTED_SLUGS, EXPECTED_JSON, EXPECTED_HTML)
    if actual != expected:
        raise ValueError(f"authorized counts mismatch: expected {expected}, got {actual}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cdx", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    digest = sha256_file(args.cdx)
    if digest != APPROVED_CDX_SHA256:
        raise ValueError(f"CDX SHA-256 mismatch: {digest}")
    selection = build_selection(json.loads(args.cdx.read_text(encoding="utf-8")), cdx_sha256=digest)
    validate_authorized_counts(selection)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(selection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"selection={args.output} sha256={sha256_file(args.output)} records={EXPECTED_SLUGS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
