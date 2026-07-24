"""Validate and expose the bounded Internet Archive source registry."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def load_registry(path: Path) -> dict[str, Any]:
    """Load a registry and reject unsafe or incomplete automated targets."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "fyi-archive.internet-archive-source-registry.v0.1.0":
        raise ValueError("unsupported Internet Archive source registry schema")
    defaults = payload.get("defaults")
    if not isinstance(defaults, dict) or defaults.get("path_suffix") != "/request/*":
        raise ValueError("registry must declare the bounded Alaveteli request path")
    if not isinstance(payload.get("targets"), list) or not payload["targets"]:
        raise ValueError("registry must contain at least one target")

    identifiers: set[str] = set()
    for target in payload["targets"]:
        _validate_target(target, identifiers)
    for target in payload.get("non_alaveteli_targets", []):
        _validate_non_alaveteli_target(target, identifiers)
    return payload


def _validate_target(target: object, identifiers: set[str]) -> None:
    if not isinstance(target, dict):
        raise ValueError("registry target must be an object")
    target = cast("dict[str, object]", target)
    identifier = target.get("instance_id")
    if (
        not isinstance(identifier, str)
        or not _ID.fullmatch(identifier)
        or identifier in identifiers
    ):
        raise ValueError("registry targets require unique, URL-safe instance_id values")
    identifiers.add(identifier)
    if target.get("platform") != "alaveteli":
        raise ValueError("automatic targets must be explicitly classified as Alaveteli")
    host = target.get("host")
    if not isinstance(host, str) or not host or "/" in host:
        raise ValueError("registry target host must be a bare hostname")
    if target.get("tier", 1) != 1:
        raise ValueError("automatic Alaveteli targets must be Tier 1")


def _validate_non_alaveteli_target(target: object, identifiers: set[str]) -> None:
    if not isinstance(target, dict):
        raise ValueError("non-Alaveteli target must be an object")
    target = cast("dict[str, object]", target)
    identifier = target.get("instance_id")
    if (
        not isinstance(identifier, str)
        or not _ID.fullmatch(identifier)
        or identifier in identifiers
    ):
        raise ValueError("non-Alaveteli targets require unique, URL-safe instance_id values")
    identifiers.add(identifier)
    required = ("platform", "host", "adapter_id", "request_path_pattern", "rights_review_status")
    if any(not isinstance(target.get(key), str) or not target[key] for key in required):
        raise ValueError(
            "non-Alaveteli targets require a platform-specific source adapter contract"
        )
    if target.get("capture_eligible") is True:
        raise ValueError("non-Alaveteli targets are catalogued only until separately enabled")


def workflow_matrix(
    path: Path,
    *,
    instance_id: str | None = None,
    capture_mode: str | None = None,
) -> dict[str, list[dict[str, str]]]:
    """Build the GitHub Actions matrix for safe Tier-1 CDX acquisition."""
    registry = load_registry(path)
    suffix = registry["defaults"]["path_suffix"]
    mode = capture_mode or registry["defaults"].get("scheduled_capture_mode", "url_index")
    if mode not in {"url_index", "all_captures"}:
        raise ValueError(f"unsupported CDX capture mode: {mode}")
    targets = registry["targets"]
    if instance_id is not None:
        targets = [target for target in targets if target["instance_id"] == instance_id]
        if not targets:
            raise ValueError(f"unknown registry instance: {instance_id}")
    return {
        "include": [
            {
                "instance": target["instance_id"],
                "host": target["host"],
                "request_path": suffix,
                "capture_mode": mode,
            }
            for target in targets
        ]
    }
