"""Reconcile public archive coverage across independent preservation channels."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

URL_FIELDS = ("url", "original", "source_url", "request_url")
TRANSFORMATION_ID = "reconcile-public-archive-completeness-v1"


@dataclass(frozen=True, slots=True)
class Inventory:
    """Normalized URL inventory and the evidence excluded from its numerator."""

    path: Path
    urls: frozenset[str]
    synthetic_urls: frozenset[str]
    duplicate_count: int
    sha256: str


def normalize_url(value: str) -> str:
    """Normalize a public URL without changing its path or query semantics."""
    split = urlsplit(value.strip())
    if split.scheme not in {"http", "https"} or not split.hostname:
        raise ValueError(f"invalid public URL: {value!r}")
    host = split.hostname.lower()
    if split.port:
        host = f"{host}:{split.port}"
    path = split.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((split.scheme.lower(), host, path, split.query, ""))


def _is_synthetic(row: dict[str, Any]) -> bool:
    state = str(row.get("state", "")).strip().lower()
    title = str(row.get("title", "")).strip().lower()
    return (
        bool(row.get("synthetic"))
        or state in {"dry-run", "synthetic", "test"}
        or title.startswith(("dry-run ", "synthetic ", "test fixture "))
    )


def _rows_from_json(path: Path) -> list[Any]:
    text = path.read_text(encoding="utf-8")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(value, dict):
        for key in ("records", "requests", "rows", "items"):
            rows = value.get(key)
            if isinstance(rows, list):
                return rows
        return [value]
    if not isinstance(value, list):
        raise ValueError(f"{path} must contain a JSON array, object, or JSONL")
    if value and isinstance(value[0], list):
        header = [str(item) for item in value[0]]
        return [dict(zip(header, row, strict=False)) for row in value[1:]]
    return value


def load_inventory(path: Path) -> Inventory:
    """Load JSON, JSONL, or CDX JSON and transparently exclude synthetic rows."""
    rows = _rows_from_json(path)
    urls: list[str] = []
    synthetic: set[str] = set()
    for raw in rows:
        if isinstance(raw, str):
            url = normalize_url(raw)
            urls.append(url)
            continue
        if not isinstance(raw, dict):
            raise ValueError(f"{path} inventory rows must be strings or objects")
        raw_url = next(
            (raw[field] for field in URL_FIELDS if isinstance(raw.get(field), str)),
            None,
        )
        if raw_url is None:
            raise ValueError(f"{path} inventory row has no supported URL field")
        url = normalize_url(raw_url)
        if _is_synthetic(raw):
            synthetic.add(url)
        else:
            urls.append(url)
    unique = frozenset(urls)
    return Inventory(
        path=path,
        urls=unique,
        synthetic_urls=frozenset(synthetic),
        duplicate_count=len(urls) - len(unique),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def _channel(expected: frozenset[str], observed: frozenset[str]) -> dict[str, Any]:
    matched = expected & observed
    missing = expected - observed
    denominator = len(expected)
    percent = 0.0 if denominator == 0 else round(100 * len(matched) / denominator, 4)
    return {
        "observed": len(observed),
        "matched": len(matched),
        "missing": len(missing),
        "percent": percent,
        "complete": bool(expected) and not missing,
        "missing_urls": sorted(missing),
        "unexpected_urls": sorted(observed - expected),
    }


def reconcile_completeness(
    *,
    site_id: str,
    enumerated: Inventory,
    primary: Inventory,
    internet_archive: Inventory,
    secondary: dict[str, Inventory] | None = None,
) -> dict[str, Any]:
    """Build a transparent public-denominator completeness report."""
    secondary = secondary or {}
    expected = enumerated.urls
    channels = {
        "primary": _channel(expected, primary.urls),
        "internet_archive": _channel(expected, internet_archive.urls),
        **{
            name: _channel(expected, inventory.urls)
            for name, inventory in sorted(secondary.items())
        },
    }
    independent_sets = [
        primary.urls,
        internet_archive.urls,
        *(item.urls for item in secondary.values()),
    ]
    at_least_one = frozenset().union(*independent_sets) if independent_sets else frozenset()
    independently_preserved = {
        url for url in expected if sum(url in values for values in independent_sets) >= 2
    }
    dual = expected & primary.urls & internet_archive.urls
    inputs = {
        "enumerated": enumerated,
        "primary": primary,
        "internet_archive": internet_archive,
        **secondary,
    }
    return {
        "schema": "fyi-archive.completeness-report.v1",
        "site_id": site_id,
        "denominator": {
            "method": "enumerated_public_urls",
            "count": len(expected),
            "planning_horizon_used": False,
            "synthetic_rows_excluded": len(enumerated.synthetic_urls),
        },
        "channels": channels,
        "minimum_preservation": _channel(expected, at_least_one),
        "dual_primary_wayback": {
            **_channel(expected, dual),
            "definition": "present in both primary capture and Internet Archive evidence",
        },
        "independent_redundancy": {
            **_channel(expected, frozenset(independently_preserved)),
            "definition": "present in at least two independent preservation channels",
        },
        "complete": channels["primary"]["complete"] and channels["internet_archive"]["complete"],
        "provenance": {
            "transformation": {
                "id": TRANSFORMATION_ID,
                "url_normalization": "lowercase scheme and host; remove fragments and non-root trailing slash; preserve query",
                "synthetic_rule": "synthetic flag or dry-run/synthetic/test state/title",
                "inference": "none",
            },
            "inputs": {
                name: {
                    "path": inventory.path.as_posix(),
                    "sha256": inventory.sha256,
                    "unique_urls": len(inventory.urls),
                    "duplicates_removed": inventory.duplicate_count,
                    "synthetic_urls_excluded": sorted(inventory.synthetic_urls),
                }
                for name, inventory in inputs.items()
            },
        },
    }
