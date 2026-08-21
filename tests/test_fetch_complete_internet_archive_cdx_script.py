from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable
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
    stale_checkpoint = tmp_path / "nested" / "cdx.pages"
    stale_checkpoint.mkdir(parents=True)
    (stale_checkpoint / "stale").write_text("discard me")
    monkeypatch.setattr(fetch_script, "fetch_complete_cdx_with_resume_key", fail)
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
    assert not (stale_checkpoint / "stale").exists()


def test_resumes_hash_verified_page_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
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
        "--max-stall-seconds",
        "60",
        "--from-timestamp",
        "2015",
        "--to-timestamp",
        "2019",
        "--include-urlkey",
        "--resume",
        "--resume-source-run-id",
        "12345",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    rows = [["https://example.test/request/1"]]
    fingerprint = fetch_script.hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()

    def first_fetch(
        *_: object,
        chunk_callback: Callable[[int, str | None, list[str], list[list[str]], str], None],
        **__: object,
    ) -> list[list[str]]:
        chunk_callback(0, "cursor-1", ["original"], rows, fingerprint)
        raise RuntimeError("deadline")

    monkeypatch.setattr(fetch_script, "fetch_complete_cdx_with_resume_key", first_fetch)
    with pytest.raises(RuntimeError, match="deadline"):
        fetch_script.main()

    observed: dict[str, object] = {}

    def resumed_fetch(*_: object, **kwargs: object) -> list[list[str]]:
        observed.update(kwargs)
        return [["original"], ["https://example.test/request/1"]]

    monkeypatch.setattr(fetch_script, "fetch_complete_cdx_with_resume_key", resumed_fetch)
    assert fetch_script.main() == 0
    assert observed["start_chunk"] == 1
    assert observed["resume_key"] == "cursor-1"
    assert observed["existing_rows"] == [["https://example.test/request/1"]]
    payload = json.loads(evidence.read_text())
    assert payload["resume_source_run_id"] == "12345"
    assert payload["page_size"] == 1000
    assert payload["from_timestamp"] == "2015"
    assert payload["to_timestamp"] == "2019"
    assert payload["include_urlkey"] is True
    assert observed["max_stall_seconds"] == 60
    assert observed["from_timestamp"] == "2015"
    assert observed["to_timestamp"] == "2019"
    assert observed["include_urlkey"] is True
    progress = capsys.readouterr().out
    assert '"event": "cdx-start"' in progress
    assert '"event": "cdx-checkpoint"' in progress
    assert '"next_resume_key_sha256"' in progress
    assert "cursor-1" not in progress


def test_reuses_completed_checkpoint_without_a_resume_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "cdx.json"
    evidence = tmp_path / "retrieval.json"
    checkpoint = tmp_path / "cdx.pages"
    checkpoint.mkdir()
    rows = [["https://example.test/request/1"]]
    fingerprint = fetch_script.hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
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
    (checkpoint / "checkpoint.json").write_text(
        json.dumps({
            "config_sha256": config_sha256,
            "completed_pages": 1,
            "next_page": 1,
            "next_resume_key": None,
            "record_count": 1,
        })
    )
    (checkpoint / "page-000000.json").write_text(
        json.dumps({"page": 0, "header": ["original"], "rows": rows, "fingerprint": fingerprint})
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
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
        ],
    )
    assert fetch_script.main() == 0
    assert json.loads(output.read_text())[1:] == rows
    payload = json.loads(evidence.read_text())
    assert payload["pagination_complete"] is True
    assert payload["checkpoint"]["resumable"] is False


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
        json.dumps({
            "config_sha256": config_sha256,
            "completed_pages": 1,
            "page_count": 2,
        })
    )
    (checkpoint / "page-000000.json").write_text(
        json.dumps({
            "page": 0,
            "header": ["original"],
            "rows": [["https://example.test/request/1"]],
            "fingerprint": "tampered",
        })
    )

    with pytest.raises(RuntimeError, match="fingerprint validation"):
        fetch_script.main()


def test_checkpoint_loader_rejects_incompatible_or_incomplete_state(tmp_path: Path) -> None:
    checkpoint = tmp_path / "pages"
    checkpoint.mkdir()
    state = checkpoint / "checkpoint.json"
    state.write_text(
        json.dumps({
            "config_sha256": "other",
            "completed_pages": 1,
            "page_count": 2,
        })
    )
    with pytest.raises(RuntimeError, match="configuration does not match"):
        fetch_script._load_checkpoint(checkpoint, config_sha256="expected")  # noqa: SLF001

    state.write_text(
        json.dumps({
            "config_sha256": "expected",
            "completed_pages": 1,
            "page_count": 2,
        })
    )
    with pytest.raises(RuntimeError, match="page 0 is missing"):
        fetch_script._load_checkpoint(checkpoint, config_sha256="expected")  # noqa: SLF001


def test_checkpoint_loader_rejects_bad_index_and_changed_header(tmp_path: Path) -> None:
    checkpoint = tmp_path / "pages"
    checkpoint.mkdir()
    (checkpoint / "checkpoint.json").write_text(
        json.dumps({
            "config_sha256": "expected",
            "completed_pages": 2,
            "page_count": 2,
        })
    )
    rows = [["https://example.test/request/1"]]
    fingerprint = fetch_script.hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    first_page = {
        "page": 1,
        "header": ["original"],
        "rows": rows,
        "fingerprint": fingerprint,
    }
    (checkpoint / "page-000000.json").write_text(json.dumps(first_page))
    with pytest.raises(RuntimeError, match="invalid index"):
        fetch_script._load_checkpoint(checkpoint, config_sha256="expected")  # noqa: SLF001

    first_page["page"] = 0
    (checkpoint / "page-000000.json").write_text(json.dumps(first_page))
    second_rows = [["https://example.test/request/2"]]
    second_fingerprint = fetch_script.hashlib.sha256(
        json.dumps(second_rows, sort_keys=True).encode()
    ).hexdigest()
    (checkpoint / "page-000001.json").write_text(
        json.dumps({
            "page": 1,
            "header": ["timestamp"],
            "rows": second_rows,
            "fingerprint": second_fingerprint,
        })
    )
    with pytest.raises(RuntimeError, match="headers are inconsistent"):
        fetch_script._load_checkpoint(checkpoint, config_sha256="expected")  # noqa: SLF001


def test_resume_arguments_must_be_supplied_together(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "fetch_complete_internet_archive_cdx.py",
            "--url-pattern",
            "example.test/request/*",
            "--instance-id",
            "example",
            "--host",
            "example.test",
            "--output",
            str(tmp_path / "cdx.json"),
            "--evidence",
            str(tmp_path / "retrieval.json"),
            "--resume",
        ],
    )
    with pytest.raises(SystemExit, match="2"):
        fetch_script.main()
