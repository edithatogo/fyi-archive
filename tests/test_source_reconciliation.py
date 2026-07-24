from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "reconcile_source_candidates",
    Path(__file__).parents[1] / "scripts" / "reconcile_source_candidates.py",
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Could not load reconciliation script")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
reconcile = _MODULE.reconcile


def test_reconcile_separates_live_capture_from_archive_only_candidate(tmp_path: Path) -> None:
    index = tmp_path / "index.json"
    index.write_text(
        json.dumps({
            "records": [
                {
                    "source": "internet_archive_cdx",
                    "source_url": "https://fyi.org.nz/request/1/title/",
                    "internet_archive_digests": ["A"],
                },
                {
                    "source": "internet_archive_cdx",
                    "source_url": "https://fyi.org.nz/request/2/old",
                    "internet_archive_digests": ["B"],
                },
            ]
        }),
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({
            "requests": [{"request_id": 1, "request_url": "https://fyi.org.nz/request/1/title"}]
        }),
        encoding="utf-8",
    )
    result = reconcile(index, manifest)
    assert result["counts"] == {"archive_only_candidate": 1, "live_captured": 1}


def test_reconcile_strips_tracking_parameters(tmp_path: Path) -> None:
    index = tmp_path / "index.json"
    index.write_text(
        json.dumps({
            "records": [{"source_url": "https://fyi.org.nz/request/3/title?fbclid=tracking"}]
        }),
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"requests": [{"request_url": "https://fyi.org.nz/request/3/title"}]}),
        encoding="utf-8",
    )
    assert reconcile(index, manifest)["counts"] == {"live_captured": 1}
