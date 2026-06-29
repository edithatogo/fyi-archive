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
