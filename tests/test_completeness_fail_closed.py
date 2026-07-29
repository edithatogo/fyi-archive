import json

import pytest

from fyi_archive.completeness import load_inventory, reconcile_completeness


def test_empty_enumeration_never_proves_completeness(tmp_path) -> None:
    paths = []
    for name in ("enumerated", "primary", "internet-archive"):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps([]), encoding="utf-8")
        paths.append(path)

    report = reconcile_completeness(
        site_id="empty",
        enumerated=load_inventory(paths[0]),
        primary=load_inventory(paths[1]),
        internet_archive=load_inventory(paths[2]),
    )

    assert report["denominator"]["count"] == 0
    assert report["channels"]["primary"]["percent"] == pytest.approx(0.0)
    assert report["channels"]["primary"]["complete"] is False
    assert report["channels"]["internet_archive"]["complete"] is False
    assert report["complete"] is False
