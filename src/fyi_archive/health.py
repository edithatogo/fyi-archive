"""Archive health and mirror parity calculations."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def manifest_count(manifest_path: Path) -> tuple[int, str | None]:
    """Return manifest record count and generated timestamp."""
    if not manifest_path.exists():
        return 0, None
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    meta = data.get("meta", {})
    record_count = int(meta.get("record_count") or data.get("record_count") or 0)
    return record_count, meta.get("generated_at")


def mirror_counts_from_env() -> dict[str, int]:
    """Read mirror counts from environment variables."""
    return {
        "huggingface": int(os.environ.get("HF_RECORD_COUNT", "0")),
        "osf": int(os.environ.get("OSF_RECORD_COUNT", "0")),
        "zenodo": int(os.environ.get("ZENODO_RECORD_COUNT", "0")),
    }


def _env_int(name: str) -> int | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def live_mirror_counts() -> dict[str, dict[str, Any]]:
    """Resolve mirror record counts from live services when credentials exist.

    Preference order per mirror:
    1. Explicit ``*_RECORD_COUNT`` env override when set (including ``0``)
    2. Live remote query when token/id env vars are present
    3. Zero with ``source=unavailable``
    """
    counts: dict[str, dict[str, Any]] = {}

    # Positive env overrides win; zero/empty means attempt a live query.
    # (Previously the monitor forced RECORD_COUNT=0 and never hit HF.)
    hf_override = _env_int("HF_RECORD_COUNT")
    if hf_override is not None and hf_override > 0:
        counts["huggingface"] = {
            "count": hf_override,
            "last_updated": None,
            "source": "env",
        }
    else:
        counts["huggingface"] = _live_huggingface_count()

    zenodo_override = _env_int("ZENODO_RECORD_COUNT")
    if zenodo_override is not None and zenodo_override > 0:
        counts["zenodo"] = {
            "count": zenodo_override,
            "last_updated": None,
            "source": "env",
        }
    else:
        counts["zenodo"] = _live_zenodo_count()

    osf_override = _env_int("OSF_RECORD_COUNT")
    if osf_override is not None and osf_override > 0:
        counts["osf"] = {"count": osf_override, "last_updated": None, "source": "env"}
    else:
        counts["osf"] = _live_osf_count()

    return counts


def _live_huggingface_count() -> dict[str, Any]:
    repo_id = os.environ.get("HF_REPO_ID", "").strip()
    token = os.environ.get("HF_TOKEN", "").strip() or None
    if not repo_id or not token:
        return {
            "count": int(os.environ.get("HF_RECORD_COUNT", "0") or 0),
            "last_updated": None,
            "source": "env" if os.environ.get("HF_RECORD_COUNT") else "unavailable",
        }
    try:
        from fyi_archive.backfill_verification import remote_huggingface_record_count

        info = remote_huggingface_record_count(repo_id=repo_id, token=token)
        return {
            "count": int(info["record_count"]),
            "last_updated": None,
            "source": "huggingface",
            "repo_id": repo_id,
            "manifest_sha256": info.get("manifest_sha256"),
        }
    except Exception as exc:  # noqa: BLE001 - doctor must remain resilient
        return {
            "count": 0,
            "last_updated": None,
            "source": "error",
            "error": str(exc),
            "repo_id": repo_id,
        }


def _live_zenodo_count() -> dict[str, Any]:
    token = os.environ.get("ZENODO_TOKEN", "").strip()
    raw_id = os.environ.get("ZENODO_DEPOSITION_ID", "").strip()
    if not token or not raw_id:
        return {
            "count": int(os.environ.get("ZENODO_RECORD_COUNT", "0") or 0),
            "last_updated": None,
            "source": "env" if os.environ.get("ZENODO_RECORD_COUNT") else "unavailable",
        }
    try:
        from fyi_archive.backfill_verification import remote_zenodo_record_count
        from fyi_archive.publish.zenodo_publish import ZENODO_API

        deposition_id = int(raw_id)
        api_url = os.environ.get("ZENODO_API_URL", ZENODO_API)
        info = remote_zenodo_record_count(token=token, deposition_id=deposition_id, api_url=api_url)
        return {
            "count": int(info["record_count"]),
            "last_updated": None,
            "source": "zenodo",
            "deposition_id": deposition_id,
            "doi": info.get("doi"),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "count": 0,
            "last_updated": None,
            "source": "error",
            "error": str(exc),
        }


def _live_osf_count() -> dict[str, Any]:
    """Best-effort OSF count via latest_manifest.json on the parent node."""
    token = os.environ.get("OSF_TOKEN", "").strip()
    node_id = (
        os.environ.get("OSF_NODE_ID", "").strip() or os.environ.get("OSF_PARENT_ID", "").strip()
    )
    if not token or not node_id:
        return {
            "count": int(os.environ.get("OSF_RECORD_COUNT", "0") or 0),
            "last_updated": None,
            "source": "env" if os.environ.get("OSF_RECORD_COUNT") else "unavailable",
        }
    try:
        import httpx

        from fyi_archive.publish.osf_publish import list_files

        files = list_files(token=token, node_id=node_id)
        manifest = next((item for item in files if item.name == "latest_manifest.json"), None)
        if manifest is None or not manifest.url:
            # No published OSF mirror yet — treat as unavailable so parity does not
            # fail the doctor solely because OSF lags HF/Zenodo.
            return {
                "count": 0,
                "last_updated": None,
                "source": "unavailable",
                "node_id": node_id,
                "note": "latest_manifest.json not found on node",
            }
        response = httpx.get(
            manifest.url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        record_count = int(
            data.get("meta", {}).get("record_count") or data.get("record_count") or 0
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "count": 0,
            "last_updated": None,
            "source": "error",
            "error": str(exc),
            "node_id": node_id,
        }
    else:
        return {
            "count": record_count,
            "last_updated": None,
            "source": "osf",
            "node_id": node_id,
        }


def parity_report(
    *,
    manifest_records: int,
    mirror_records: dict[str, int],
    tolerance: int,
) -> dict[str, Any]:
    """Build mirror parity report."""
    mirrors = {}
    healthy = True
    for name, count in sorted(mirror_records.items()):
        difference = manifest_records - count
        within_tolerance = abs(difference) <= tolerance
        healthy = healthy and within_tolerance
        mirrors[name] = {
            "count": count,
            "difference_from_manifest": difference,
            "within_tolerance": within_tolerance,
        }
    return {
        "healthy": healthy,
        "tolerance": tolerance,
        "manifest_records": manifest_records,
        "mirrors": mirrors,
    }
