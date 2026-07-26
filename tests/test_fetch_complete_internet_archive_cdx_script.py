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
    assert payload["record_count"] == 0
    assert payload["checkpoint"]["completed_pages"] == 0
    assert payload["checkpoint"]["resumable"] is False
    assert payload["failure"] == {
        "message": "CDX acquisition exceeded whole-run deadline",
        "type": "RuntimeError",
    }
    assert payload["retrieved_at"].endswith("Z")
    assert not output.exists()


def test_resumes_hash_verified_page_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "cdx.json"
    evidence = tmp_path / "retrieval.json"
    argv = [
        "fetch_complete_internet_archive_cdx.py",
        "--url-pattern",
        "example.test/request/*",
        "--instance-id",
        "example",
        "--host",
        "example.test",
        "--capture-mode",
        "all_captures",
        "--output",
        str(output),
        "--evidence",
        str(evidence),
        "--resume",
        "--resume-source-run-id",
        "12345",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    rows = [["https://example.test/request/1"]]
    fingerprint = fetch_script.hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()

    def first_fetch(*_: object, page_callback: object, **__: object) -> list[list[str]]:
        assert callable(page_callback)
        page_callback(0, 2, ["original"], rows, fingerprint)
        raise RuntimeError("deadline")

    monkeypatch.setattr(fetch_script, "fetch_complete_cdx", first_fetch)
    with pytest.raises(RuntimeError, match="deadline"):
        fetch_script.main()

    observed: dict[str, object] = {}

    def resumed_fetch(*_: object, **kwargs: object) -> list[list[str]]:
        observed.update(kwargs)
        return [["original"], ["https://example.test/request/1"]]

    monkeypatch.setattr(fetch_script, "fetch_complete_cdx", resumed_fetch)
    assert fetch_script.main() == 0
    assert observed["start_page"] == 1
    assert observed["existing_rows"] == [["https://example.test/request/1"]]
    assert json.loads(evidence.read_text())["resume_source_run_id"] == "12345"


def test_rejects_tampered_checkpoint_page(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "cdx.json"
    evidence = tmp_path / "retrieval.json"
    argv = [
        "fetch_complete_internet_archive_cdx.py",
        "--url-pattern",
        "example.test/request/*",
        "--instance-id",
        "example",
        "--host",
        "example.test",
        "--capture-mode",
        "all_captures",
        "--output",
        str(output),
        "--evidence",
        str(evidence),
        "--resume",
        "--resume-source-run-id",
        "12345",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    config_sha256 = fetch_script._config_hash(  # noqa: SLF001
        fetch_script.argparse.Namespace(
            url_pattern="example.test/request/*",
            instance_id="example",
            host="example.test",
            page_size=1000,
            max_pages=100,
            capture_mode="all_captures",
        )
    )
    checkpoint = tmp_path / "cdx.pages"
    checkpoint.mkdir()
    (checkpoint / "checkpoint.json").write_text(
        json.dumps(
            {
                "config_sha256": config_sha256,
                "completed_pages": 1,
                "page_count": 2,
            }
        )
    )
    (checkpoint / "page-000000.json").write_text(
        json.dumps(
            {
                "page": 0,
                "header": ["original"],
                "rows": [["https://example.test/request/1"]],
                "fingerprint": "tampered",
            }
        )
    )

    with pytest.raises(RuntimeError, match="fingerprint validation"):
        fetch_script.main()
