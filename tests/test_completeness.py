from __future__ import annotations

import json
from pathlib import Path

import pytest

from fyi_archive.completeness import load_inventory, normalize_url, reconcile_completeness


def _write(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_completeness_excludes_synthetic_and_reports_independent_channels(
    tmp_path: Path,
) -> None:
    enumerated = load_inventory(
        _write(
            tmp_path / "enumerated.json",
            [
                {"url": "https://example.test/request/1", "state": "dry-run"},
                {"url": "https://example.test/request/2/"},
                {"url": "https://example.test/request/3"},
            ],
        )
    )
    primary = load_inventory(
        _write(
            tmp_path / "primary.json",
            [
                {"source_url": "https://example.test/request/2"},
            ],
        )
    )
    internet_archive = load_inventory(
        _write(
            tmp_path / "ia.json",
            [
                ["original", "timestamp"],
                ["https://example.test/request/2/", "20200101000000"],
                ["https://example.test/request/3", "20200101000000"],
            ],
        )
    )
    secondary = load_inventory(
        _write(tmp_path / "secondary.jsonl", [{"url": "https://example.test/request/3"}])
    )
    report = reconcile_completeness(
        site_id="example",
        enumerated=enumerated,
        primary=primary,
        internet_archive=internet_archive,
        secondary={"national": secondary},
    )
    assert report["denominator"] == {
        "method": "enumerated_public_urls",
        "count": 2,
        "planning_horizon_used": False,
        "synthetic_rows_excluded": 1,
    }
    assert report["channels"]["primary"]["percent"] == pytest.approx(50.0)
    assert report["channels"]["internet_archive"]["percent"] == pytest.approx(100.0)
    assert report["minimum_preservation"]["complete"] is True
    assert report["dual_primary_wayback"]["percent"] == pytest.approx(50.0)
    assert report["independent_redundancy"]["percent"] == pytest.approx(100.0)
    assert report["complete"] is False
    assert report["provenance"]["inputs"]["enumerated"]["synthetic_urls_excluded"] == [
        "https://example.test/request/1"
    ]


def test_inventory_reports_duplicates_and_rejects_missing_url(tmp_path: Path) -> None:
    inventory = load_inventory(
        _write(
            tmp_path / "rows.json",
            [
                "https://EXAMPLE.test/request/1/",
                "https://example.test/request/1#fragment",
            ],
        )
    )
    assert inventory.urls == frozenset({"https://example.test/request/1"})
    assert inventory.duplicate_count == 1
    with pytest.raises(ValueError, match="no supported URL field"):
        load_inventory(_write(tmp_path / "bad.json", [{"title": "no URL"}]))


@pytest.mark.parametrize("value", ["", "/request/1", "ftp://example.test/a"])
def test_normalize_url_rejects_non_public_urls(value: str) -> None:
    with pytest.raises(ValueError, match="invalid public URL"):
        normalize_url(value)
