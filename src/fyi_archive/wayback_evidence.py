"""Independent validation for retained Wayback site artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

from fyi_archive.internet_archive_cdx import CDX_ENDPOINT


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _child_path(root: Path, value: object) -> Path:
    relative = Path(str(value))
    if relative.is_absolute():
        raise RuntimeError("artifact path must be relative")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise RuntimeError("artifact path escapes its retained root") from error
    return candidate


def _config_sha256(retrieval: dict[str, Any], *, page_size: int) -> str:
    config: dict[str, object] = {
        "url_pattern": retrieval["url_pattern"],
        "instance_id": retrieval["instance_id"],
        "host": retrieval["host"],
        "page_size": page_size,
        "capture_mode": retrieval["capture_mode"],
        "pagination_mode": "resume_key",
        "endpoint": CDX_ENDPOINT,
    }
    for field in ("from_timestamp", "to_timestamp"):
        if retrieval.get(field) is not None:
            config[field] = retrieval[field]
    if retrieval.get("include_urlkey") is True:
        config["include_urlkey"] = True
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def verify_site_artifact(root: Path, *, default_page_size: int = 1000) -> dict[str, Any]:
    """Validate every manifest-referenced retrieval, checkpoint, page, and export."""
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("pagination", {}).get("mode") != "resume_key":
        raise RuntimeError("manifest pagination mode is not resume_key")
    raw_artifacts = manifest.get("artifacts")
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        raise RuntimeError("manifest has no artifacts")
    artifacts = cast("list[object]", raw_artifacts)

    total_records = 0
    total_pages = 0
    complete_artifacts = 0
    resumable_artifacts = 0
    retrievals: list[dict[str, object]] = []
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            raise RuntimeError(f"artifact {index} is not an object")
        artifact = cast("dict[str, Any]", artifact)
        evidence_path = _child_path(root, artifact["evidence_path"])
        retrieval = json.loads(evidence_path.read_text(encoding="utf-8"))
        if _sha256(evidence_path) != artifact.get("evidence_sha256"):
            raise RuntimeError(f"artifact {index} evidence hash does not match")
        if retrieval.get("pagination_mode") != "resume_key":
            raise RuntimeError(f"artifact {index} pagination mode is not resume_key")
        page_size = int(retrieval.get("page_size", default_page_size))
        config_sha256 = _config_sha256(retrieval, page_size=page_size)
        checkpoint_dir = root / f"cdx-{index:02d}.pages"
        checkpoint = json.loads((checkpoint_dir / "checkpoint.json").read_text(encoding="utf-8"))
        retrieval_checkpoint = retrieval.get("checkpoint")
        if not isinstance(retrieval_checkpoint, dict):
            raise RuntimeError(f"artifact {index} has no retrieval checkpoint")
        if not (
            config_sha256
            == checkpoint.get("config_sha256")
            == retrieval_checkpoint.get("config_sha256")
        ):
            raise RuntimeError(f"artifact {index} configuration hash does not match")
        completed_pages = int(checkpoint["completed_pages"])
        page_paths = sorted(checkpoint_dir.glob("page-*.json"))
        if not (len(page_paths) == completed_pages == int(retrieval_checkpoint["completed_pages"])):
            raise RuntimeError(f"artifact {index} page count does not match")
        header: list[str] | None = None
        fingerprints: set[str] = set()
        record_count = 0
        for page_index, page_path in enumerate(page_paths):
            page = json.loads(page_path.read_text(encoding="utf-8"))
            if page.get("page") != page_index:
                raise RuntimeError(f"artifact {index} page indices are not contiguous")
            current_header = [str(value) for value in page["header"]]
            if header is None:
                header = current_header
            elif current_header != header:
                raise RuntimeError(f"artifact {index} page headers are inconsistent")
            rows = [[str(value) for value in row] for row in page["rows"]]
            fingerprint = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
            if page.get("fingerprint") != fingerprint or fingerprint in fingerprints:
                raise RuntimeError(f"artifact {index} page fingerprint is invalid or repeated")
            fingerprints.add(fingerprint)
            record_count += len(rows)
        if not (
            record_count
            == int(checkpoint["record_count"])
            == int(retrieval["record_count"])
            == int(artifact["record_count"])
        ):
            raise RuntimeError(f"artifact {index} record counts do not match")

        retrieval_complete = (
            retrieval.get("retrieval_status") == "complete"
            and retrieval.get("pagination_complete") is True
        )
        if retrieval_complete:
            export_path = _child_path(root, artifact["path"])
            response_sha256 = _sha256(export_path)
            if not (response_sha256 == retrieval.get("response_sha256") == artifact.get("sha256")):
                raise RuntimeError(f"artifact {index} response hash does not match")
            export = json.loads(export_path.read_text(encoding="utf-8"))
            if len(export) - 1 != record_count:
                raise RuntimeError(f"artifact {index} export count does not match")
            if retrieval_checkpoint.get("resumable") is not False:
                raise RuntimeError(f"artifact {index} complete retrieval is resumable")
            if checkpoint.get("next_resume_key") is not None:
                raise RuntimeError(f"artifact {index} complete checkpoint retains a cursor")
            if retrieval_checkpoint.get("next_resume_key") is not None:
                raise RuntimeError(f"artifact {index} complete retrieval retains a cursor")
            next_resume_key_sha256 = None
            resumable = False
            complete_artifacts += 1
        else:
            if retrieval.get("retrieval_status") != "failed":
                raise RuntimeError(f"artifact {index} is neither complete nor failed")
            next_resume_key = checkpoint.get("next_resume_key")
            resumable = retrieval_checkpoint.get("resumable") is True
            failed_open = (
                retrieval.get("response_sha256") is not None or artifact.get("path") is not None
            )
            cursor_mismatch = retrieval_checkpoint.get("next_resume_key") != next_resume_key
            resume_invalid = (resumable and not next_resume_key) or (
                not resumable and next_resume_key is not None
            )
            if failed_open or cursor_mismatch or resume_invalid:
                raise RuntimeError(f"artifact {index} failed-open or has invalid resume state")
            next_resume_key_sha256 = (
                hashlib.sha256(str(next_resume_key).encode()).hexdigest()
                if next_resume_key is not None
                else None
            )
            resumable_artifacts += int(resumable)
        total_records += record_count
        total_pages += completed_pages
        retrievals.append({
            "index": index,
            "complete": retrieval_complete,
            "resumable": resumable,
            "record_count": record_count,
            "completed_pages": completed_pages,
            "config_sha256": config_sha256,
            "next_resume_key_sha256": next_resume_key_sha256,
        })

    manifest_complete = manifest.get("complete") is True
    if manifest_complete != (complete_artifacts == len(artifacts)):
        raise RuntimeError("manifest completeness does not match its artifacts")
    return {
        "schema": "fyi-archive.wayback-verification.v1",
        "site_id": manifest["site_id"],
        "country": manifest["country"],
        "complete": manifest_complete,
        "resumable": resumable_artifacts > 0,
        "record_count": total_records,
        "completed_pages": total_pages,
        "resume_source_run_id": manifest.get("resume", {}).get("source_run_id"),
        "retrievals": retrievals,
    }


def find_site_count(root: Path, site_id: str) -> int | None:
    """Find one site's retained manifest count below a run artifact root."""
    matches: list[int] = []
    for manifest_path in root.rglob("manifest.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("site_id") == site_id:
            matches.append(sum(int(item["record_count"]) for item in manifest.get("artifacts", [])))
    if not matches:
        return None
    if len(matches) > 1:
        raise RuntimeError(f"multiple manifests found for site {site_id}")
    return matches[0]
