"""Deterministic, publication-free packaging for FOI-O candidate outputs."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from fyi_archive.derived_layer import validate_derived_manifest

BUNDLE_SCHEMA = "fyi-archive.foi-o-derived-bundle.v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_object(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return document


def _load_candidates(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number} must contain a JSON object")
            candidate_id = row.get("candidate_id")
            if not isinstance(candidate_id, str) or not candidate_id:
                raise ValueError(f"{path}:{line_number} requires candidate_id")
            forbidden = {"message_body", "request_body", "ocr_text", "attachment_bytes"}
            leaked = sorted(forbidden.intersection(row))
            if leaked:
                raise ValueError(f"{path}:{line_number} contains forbidden raw fields: {leaked}")
            rows.append(row)
    ids = [str(row["candidate_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path} contains duplicate candidate_id values")
    return rows


def candidate_delta(
    baseline: list[dict[str, Any]], current: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return a deterministic candidate-level baseline delta."""
    before = {str(row["candidate_id"]): row for row in baseline}
    after = {str(row["candidate_id"]): row for row in current}
    shared = before.keys() & after.keys()
    changed = sorted(
        candidate_id
        for candidate_id in shared
        if json.dumps(before[candidate_id], sort_keys=True)
        != json.dumps(after[candidate_id], sort_keys=True)
    )
    return {
        "baseline_count": len(before),
        "current_count": len(after),
        "added": sorted(after.keys() - before.keys()),
        "removed": sorted(before.keys() - after.keys()),
        "changed": changed,
    }


def package_derived_layer(
    *,
    manifest_path: Path,
    candidates_path: Path,
    output_dir: Path,
    baseline_path: Path | None = None,
) -> dict[str, Any]:
    """Create a deterministic local bundle without uploading or publishing it."""
    manifest = _load_json_object(manifest_path)
    validation = validate_derived_manifest(manifest)
    if not validation["ok"]:
        raise ValueError("invalid derived manifest: " + "; ".join(validation["errors"]))
    if manifest.get("release_status") != "draft":
        raise ValueError("local packaging requires release_status=draft")

    current = _load_candidates(candidates_path)
    baseline = _load_candidates(baseline_path) if baseline_path else []
    delta = candidate_delta(baseline, current)

    output_dir.mkdir(parents=True, exist_ok=True)
    staged_manifest = output_dir / "derived-manifest.json"
    staged_candidates = output_dir / "candidates.ndjson"
    shutil.copyfile(manifest_path, staged_manifest)
    shutil.copyfile(candidates_path, staged_candidates)

    bundle = {
        "schema": BUNDLE_SCHEMA,
        "publication_status": "not_published",
        "candidate_status": "candidate",
        "record_count": len(current),
        "artifacts": [
            {
                "path": staged_candidates.name,
                "sha256": _sha256(staged_candidates),
                "bytes": staged_candidates.stat().st_size,
            },
            {
                "path": staged_manifest.name,
                "sha256": _sha256(staged_manifest),
                "bytes": staged_manifest.stat().st_size,
            },
        ],
        "baseline_delta": delta,
    }
    bundle_path = output_dir / "bundle-manifest.json"
    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return bundle


def verify_derived_bundle(output_dir: Path) -> dict[str, Any]:
    """Round-trip verify a locally packaged FOI-O derived bundle."""
    bundle = _load_json_object(output_dir / "bundle-manifest.json")
    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError(f"bundle schema must be {BUNDLE_SCHEMA}")
    if bundle.get("publication_status") != "not_published":
        raise ValueError("local bundle must retain publication_status=not_published")

    artifacts = bundle.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("bundle artifacts must be a non-empty array")
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ValueError("bundle artifact must be an object")
    artifact_names = [artifact.get("path") for artifact in artifacts]
    if any(not isinstance(name, str) for name in artifact_names) or sorted(
        str(name) for name in artifact_names
    ) != ["candidates.ndjson", "derived-manifest.json"]:
        raise ValueError("bundle artifacts must contain only the expected local files")
    for artifact in artifacts:
        path = output_dir / str(artifact.get("path", ""))
        if not path.is_file():
            raise ValueError(f"bundle artifact is missing: {path.name}")
        if _sha256(path) != artifact.get("sha256"):
            raise ValueError(f"bundle artifact digest mismatch: {path.name}")
        if path.stat().st_size != artifact.get("bytes"):
            raise ValueError(f"bundle artifact size mismatch: {path.name}")

    manifest = _load_json_object(output_dir / "derived-manifest.json")
    validation = validate_derived_manifest(manifest)
    if not validation["ok"]:
        raise ValueError("packaged derived manifest is invalid")
    candidates = _load_candidates(output_dir / "candidates.ndjson")
    if len(candidates) != bundle.get("record_count"):
        raise ValueError("bundle candidate count does not match candidates.ndjson")
    return {
        "verified": True,
        "record_count": len(candidates),
        "publication_status": bundle["publication_status"],
    }
