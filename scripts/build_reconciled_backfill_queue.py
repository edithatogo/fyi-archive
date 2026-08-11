"""Build a deterministic fyi-cli queue from a completed reconciled source inventory."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlparse


def request_slug(url: object) -> str:
    path = urlparse(str(url or "")).path.rstrip("/")
    prefix = "/request/"
    if not path.startswith(prefix):
        return ""
    slug = path.removeprefix(prefix)
    # HTML and JSON representations identify the same logical request.
    if slug.endswith(".json"):
        slug = slug.removesuffix(".json")
    return slug if slug and "/" not in slug else ""


def _archive_candidates(index: Mapping[str, object]) -> dict[str, list[dict[str, object]]]:
    records = index.get("records")
    if not isinstance(records, list):
        raise ValueError("source index has no records")
    candidates: dict[str, list[dict[str, object]]] = {}
    for row in records:
        if not isinstance(row, dict):
            continue
        slug = request_slug(row.get("source_url"))
        if slug:
            candidates.setdefault(slug, []).append(row)
    return candidates


def _canonical_manifest_queue(
    manifest: Mapping[str, object], candidates: Mapping[str, list[dict[str, object]]]
) -> list[dict[str, object]]:
    meta = manifest.get("meta")
    source = meta.get("source") if isinstance(meta, dict) else None
    requests = manifest.get("requests")
    if not isinstance(source, str) or not source:
        raise ValueError("captured manifest has no canonical source URL")
    if not isinstance(requests, list):
        raise ValueError("captured manifest has no requests")

    queue: list[dict[str, object]] = []
    request_ids: set[int | str] = set()
    titles: set[str] = set()
    for request in requests:
        if not isinstance(request, dict) or request.get("state") == "dry-run":
            continue
        request_id = request.get("request_id")
        title = request.get("url_title")
        if (
            isinstance(request_id, bool)
            or not isinstance(request_id, (int, str))
            or not str(request_id)
        ):
            raise ValueError("captured manifest contains an invalid request_id")
        if not isinstance(title, str) or not title:
            raise ValueError("captured manifest contains an invalid url_title")
        if request_id in request_ids or title in titles:
            raise ValueError("captured manifest contains duplicate request identities")
        request_ids.add(request_id)
        titles.add(title)
        archive_rows = candidates.get(title, [])
        archive_urls = sorted({
            str(row["source_url"])
            for row in archive_rows
            if isinstance(row.get("source_url"), str) and row["source_url"]
        })
        archive_digests = sorted({
            str(digest)
            for row in archive_rows
            if isinstance(row.get("internet_archive_digests"), list)
            for digest in row["internet_archive_digests"]
            if isinstance(digest, str) and digest
        })
        queue.append({
            "request_id": request_id,
            "url_title": title,
            "source_url": f"{source.rstrip('/')}/request/{title}",
            "archive_source_urls": archive_urls,
            "archive_digests": archive_digests,
        })
    if not queue:
        raise ValueError("captured manifest has no non-dry-run requests")
    return sorted(
        queue,
        key=lambda row: (
            (
                0,
                int(row["request_id"]),
            )
            if isinstance(row["request_id"], int)
            or (isinstance(row["request_id"], str) and row["request_id"].isdigit())
            else (1, str(row["request_id"]))
        ),
    )


def build_queue(
    index: Mapping[str, object],
    retrieval: Mapping[str, object],
    manifest: Mapping[str, object] | None = None,
) -> list[dict[str, object]]:
    if retrieval.get("retrieval_status") != "complete" or not retrieval.get("pagination_complete"):
        raise ValueError("reconciled source inventory is incomplete")
    candidates = _archive_candidates(index)
    if manifest is not None:
        return _canonical_manifest_queue(manifest, candidates)
    queue: dict[str, dict[str, str]] = {}
    for rows in candidates.values():
        for row in rows:
            source_url = str(row.get("source_url") or "")
            slug = request_slug(source_url)
            if not slug:
                continue
            candidate = {"request_id": slug, "url_title": slug, "source_url": source_url}
            existing = queue.get(slug)
            # Prefer the canonical HTML URL when both representations are present.
            if existing is None or str(existing["source_url"]).endswith(".json"):
                queue[slug] = candidate
    if not queue:
        raise ValueError("completed source inventory has no canonical request URLs")
    return [queue[key] for key in sorted(queue)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-index", type=Path, required=True)
    parser.add_argument("--retrieval-evidence", type=Path, required=True)
    parser.add_argument("--captured-manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    queue = build_queue(
        json.loads(args.source_index.read_text(encoding="utf-8")),
        json.loads(args.retrieval_evidence.read_text(encoding="utf-8")),
        (
            json.loads(args.captured_manifest.read_text(encoding="utf-8"))
            if args.captured_manifest
            else None
        ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in queue), encoding="utf-8"
    )
    print(json.dumps({"queue_count": len(queue), "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
