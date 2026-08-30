"""Validate and atomically store the public, non-secret sync result."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fyi_archive.instances import get_instance


def validate_summary(summary: dict[str, Any], *, instance_id: str) -> None:
    """Reject invalid or cross-instance metadata before producing a card."""
    get_instance(instance_id)
    if summary.get("instance_id") != instance_id:
        raise ValueError("sync summary instance does not match requested instance")
    count = summary.get("record_count")
    if type(count) is not int or count < 0:
        raise ValueError("sync summary record_count must be a nonnegative integer")
    digest = summary.get("manifest_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or set(digest) - set("0123456789abcdef"):
        raise ValueError("sync summary manifest_sha256 must be a SHA-256 digest")
    verified = summary.get("verified")
    if "verified" not in summary or (verified is not None and type(verified) is not bool):
        raise ValueError("sync summary verified must be a boolean or null")
    generated_at = summary.get("generated_at")
    if not isinstance(generated_at, str) or datetime.fromisoformat(generated_at).tzinfo is None:
        raise ValueError("sync summary generated_at must include a timezone")


def write_summary(path: Path, summary: dict[str, Any], *, instance_id: str) -> None:
    """Write a complete JSON artifact atomically, even across interruptions."""
    validate_summary(summary, instance_id=instance_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(summary, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        Path(temporary).replace(path)
    finally:
        Path(temporary).unlink(missing_ok=True)
