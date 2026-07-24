from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path("scripts/fetch_complete_internet_archive_cdx.py")
SPEC = importlib.util.spec_from_file_location("fetch_complete_internet_archive_cdx", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
fetch_script = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = fetch_script
SPEC.loader.exec_module(fetch_script)


def test_writes_failure_evidence_without_a_partial_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_: object, **__: object) -> list[list[str]]:
        raise RuntimeError("CDX acquisition exceeded whole-run deadline")

    output = tmp_path / "nested" / "cdx.json"
    evidence = tmp_path / "nested" / "retrieval.json"
    monkeypatch.setattr(fetch_script, "fetch_complete_cdx", fail)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "fetch_complete_internet_archive_cdx.py",
            "--url-pattern",
            "www.righttoknow.org.au/request/*",
            "--instance-id",
            "au-rtk",
            "--host",
            "www.righttoknow.org.au",
            "--capture-mode",
            "all_captures",
            "--output",
            str(output),
            "--evidence",
            str(evidence),
        ],
    )

    with pytest.raises(RuntimeError, match="whole-run deadline"):
        fetch_script.main()

    assert not output.exists()
    payload = json.loads(evidence.read_text())
    assert payload["retrieval_status"] == "failed"
    assert payload["capture_mode"] == "all_captures"
    assert payload["pagination_complete"] is False
    assert payload["response_sha256"] is None
    assert payload["record_count"] is None
    assert payload["failure"] == {
        "message": "CDX acquisition exceeded whole-run deadline",
        "type": "RuntimeError",
    }
    assert payload["retrieved_at"].endswith("Z")
    assert not output.exists()
