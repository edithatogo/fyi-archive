"""Exercise the archive handoff with the actual Rust verifier and event exporter."""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import zipfile
from dataclasses import replace
from functools import partial
from pathlib import Path
from typing import Any

import polars as pl
import pytest
from warcio.archiveiterator import ArchiveIterator

from fyi_archive import offline_seed
from fyi_archive.archive_package import (
    EvidenceFile,
    PackageInputs,
    build_archive_package,
    verify_package_store,
)
from fyi_archive.offline_seed import SourceEvidence, capture_offline_evidence
from fyi_archive.process_projection import build_process_projection, verify_process_projection
from fyi_archive.seed import CaptureError, SeedCaps, SeedRequest, load_ledger, run_seed

FIXTURE = Path(__file__).parent / "fixtures" / "offline-seed-v1"
REQUEST = SeedRequest(701, "fictional_seed_case", "Fictional records request", "fictional-office")
CAPTURED_AT = "2026-01-04T00:00:00Z"
MEDIA_TYPES = {
    ".raw": "application/octet-stream",
    ".json": "application/json",
    ".wacz": "application/wacz",
}


@pytest.fixture
def rust_cli() -> Path:
    path = os.environ.get("FYI_OFFLINE_SEED_CLI")
    if not path:
        pytest.skip("requires the Rust fyi-cli built by the dedicated offline seed workflow")
    binary = Path(path)
    if not binary.is_absolute() or not binary.is_file() or not os.access(binary, os.X_OK):
        pytest.fail("FYI_OFFLINE_SEED_CLI must name an absolute path to an executable")
    return binary


@pytest.fixture
def source_evidence() -> tuple[SourceEvidence, ...]:
    return tuple(
        SourceEvidence(
            kind,
            FIXTURE / directory / "raw",
            FIXTURE / directory / "result.json",
            FIXTURE / directory / "receipt.json",
            FIXTURE / directory / "capture.wacz",
            FIXTURE / directory / "link.json",
        )
        for directory, kind in (
            ("json", "request-json"),
            ("page", "request-page"),
            ("attachment", "attachment"),
        )
    )


def _read_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _export(cli: Path, derived: Path, output: Path, attachments: Path, checkpoint: Path) -> None:
    subprocess.run(  # noqa: S603 - explicitly selected Rust CLI and fixed offline arguments
        [
            str(cli),
            "export-process-events",
            "--derived-dir",
            str(derived),
            "--output",
            str(output),
            "--attachments-output",
            str(attachments),
            "--checkpoint",
            str(checkpoint),
            "--captured-at",
            CAPTURED_AT,
        ],
        check=True,
        timeout=30,
    )


def _assert_packaged_evidence(package: Path, captures: tuple[SourceEvidence, ...]) -> None:
    evidence = package / "evidence"
    assert len(list(evidence.iterdir())) == 15
    for index, capture in enumerate(captures):
        for label, path, extension in (
            ("raw", capture.raw, "raw"),
            ("result", capture.result, "json"),
            ("receipt", capture.receipt, "json"),
            ("wacz", capture.wacz, "wacz"),
            ("link", capture.link, "json"),
        ):
            assert (evidence / f"{index}-{label}.{extension}").read_bytes() == path.read_bytes()
        receipt = json.loads(capture.receipt.read_bytes())
        link = json.loads(capture.link.read_bytes())
        with zipfile.ZipFile(evidence / f"{index}-wacz.wacz") as wacz:
            records = ArchiveIterator(io.BytesIO(wacz.read("archive/data.warc.gz")))
            record = next(records)
            assert record.rec_type == "response"
            assert record.rec_headers.get_header("WARC-Record-ID") == link["record_id"]
            assert (
                record.rec_headers.get_header("WARC-Target-URI") == receipt["responses"][0]["url"]
            )
            assert record.http_headers.get_statuscode() == "200"
            assert record.content_stream().read() == capture.raw.read_bytes()
            assert next(records, None) is None


def test_seed_package_and_checkpoint_rollback(
    tmp_path: Path, rust_cli: Path, source_evidence: tuple[SourceEvidence, ...]
) -> None:
    data = tmp_path / "data"
    ledger = data / "ledger.jsonl"
    offline = data / "offline-seed"
    capture = partial(capture_offline_evidence, evidence=source_evidence, verifier=rust_cli)
    seed = partial(
        run_seed,
        requests=[REQUEST],
        ledger_path=ledger,
        data_dir=data,
        derived_dir=data / "derived",
        caps=SeedCaps(max_bytes=100_000),
        dry_run=False,
        capture=capture,
    )
    summary = seed()
    assert (summary["processed"], summary["failed"]) == (1, 0)
    assert load_ledger(ledger) == {701}
    ledger_before = ledger.read_bytes()

    case = offline / "701" / "request.json"
    original_case = case.read_bytes()
    with pytest.raises(FileExistsError):
        capture(REQUEST, data, tmp_path / "dist", SeedCaps(), ())

    events = tmp_path / "events.jsonl"
    attachments = tmp_path / "attachments.jsonl"
    checkpoint = tmp_path / "checkpoint.json"
    _export(rust_cli, offline, events, attachments, checkpoint)
    checkpoint_before = checkpoint.read_bytes()
    event_rows = _read_rows(events)
    attachment_rows = _read_rows(attachments)
    assert [row["activity"] for row in event_rows] == ["sent", "response", "follow_up"]
    assert len(attachment_rows) == 1
    case_id = event_rows[0]["logical_request_id"]
    assert all(row["logical_request_id"] == case_id for row in event_rows + attachment_rows)
    link = json.loads(source_evidence[2].link.read_bytes())
    attachment = attachment_rows[0]
    assert attachment["warc_record_id"] == link["record_id"]
    assert attachment["locator"] is None
    assert attachment["byte_size"] == source_evidence[2].raw.stat().st_size

    projection = tmp_path / "projection"
    coverage = build_process_projection(
        events_path=events,
        attachments_path=attachments,
        output_dir=projection,
    )
    verify_process_projection(projection)
    assert (coverage["case_count"], coverage["event_count"], coverage["attachment_count"]) == (
        1,
        3,
        1,
    )
    assert pl.read_parquet(projection / "attachments.parquet")["warc_record_id"].to_list() == [
        link["record_id"]
    ]

    inputs = tmp_path / "inputs"
    inputs.mkdir()
    provenance = inputs / "provenance.json"
    provenance.write_text('{"source":"fictional-offline-seed"}\n', encoding="utf-8")
    retention = inputs / "retention.json"
    retention.write_text('{"status":"fictional-fixture"}\n', encoding="utf-8")
    package_inputs = PackageInputs(
        instance_id="se-handlingar",
        archive_revision=1,
        repository="https://huggingface.co/datasets/example/fictional",
        repository_revision="0123456789abcdef0123456789abcdef01234567",
        cases_path=_write_rows(
            inputs / "cases.ndjson",
            pl.read_parquet(projection / "cases.parquet").to_dicts(),
        ),
        events_path=_write_rows(
            inputs / "events.ndjson",
            [
                {
                    **row,
                    "source_sequence": row["source_order"]["event_sequence"],
                    "case_id": case_id,
                }
                for row in event_rows
            ],
        ),
        attachments_path=_write_rows(
            inputs / "attachments.ndjson",
            [{**attachment, "case_id": case_id}],
        ),
        takedown_inventory_path=_write_rows(inputs / "takedown.ndjson", []),
        provenance_path=provenance,
        retention_path=retention,
        evidence_files=tuple(
            EvidenceFile(path.name, path, MEDIA_TYPES[path.suffix])
            for path in sorted((case.parent / "evidence").iterdir())
        ),
    )
    store = tmp_path / "store"
    package = store / build_archive_package(package_inputs, store)["package_path"]
    assert verify_package_store(store)["verified"]
    assert _read_rows(package / "events.ndjson") == _read_rows(package_inputs.events_path)
    assert _read_rows(package / "attachments.ndjson")[0]["warc_record_id"] == link["record_id"]
    _assert_packaged_evidence(package, source_evidence)
    manifest_before = (package / "archive-package.json").read_bytes()

    corrupt_store = tmp_path / "corrupt-store"
    shutil.copytree(store, corrupt_store)
    corrupt = corrupt_store / package.relative_to(store) / "evidence" / "2-wacz.wacz"
    _corrupt(corrupt)
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_package_store(corrupt_store)

    # Advance the exporter checkpoint by removing a follow-up in the derived work copy.
    changed = json.loads(original_case)
    changed["info_request_events"].pop()
    case.write_text(json.dumps(changed), encoding="utf-8")
    ledger.unlink()
    deletion = tmp_path / "deletion.jsonl"
    _export(rust_cli, offline, deletion, attachments, checkpoint)
    deleted = _read_rows(deletion)
    assert [(row["event_id"], row["operation"], row["revision"]) for row in deleted] == [
        (event_rows[-1]["event_id"], "delete", 2),
    ]
    assert checkpoint.read_bytes() != checkpoint_before
    combined = _write_rows(tmp_path / "combined.jsonl", event_rows + deleted)
    changed_coverage = build_process_projection(
        events_path=combined,
        attachments_path=attachments,
        output_dir=tmp_path / "changed",
    )
    assert (changed_coverage["event_count"], changed_coverage["retracted_event_count"]) == (2, 1)

    case.write_bytes(original_case)
    checkpoint.write_bytes(checkpoint_before)
    ledger.write_bytes(ledger_before)
    resumed = seed()
    assert (resumed["processed"], resumed["skipped"]) == (0, 1)
    replay = tmp_path / "replay.jsonl"
    _export(rust_cli, offline, replay, attachments, checkpoint)
    assert _read_rows(replay) == []
    assert _read_rows(attachments) == attachment_rows
    assert ledger.read_bytes() == ledger_before
    assert checkpoint.read_bytes() == checkpoint_before
    assert (package / "archive-package.json").read_bytes() == manifest_before
    assert verify_package_store(store)["verified"]


def _corrupt(path: Path) -> None:
    original = path.read_bytes()
    path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))


@pytest.mark.parametrize(
    "failure",
    [
        "tampered-wacz",
        "missing-response",
        "wrong-resource",
        "wrong-case",
        "missing-attachment",
        "transfer-byte-cap",
        "derived-byte-cap",
    ],
)
def test_seed_rejects_incomplete_evidence(
    tmp_path: Path, rust_cli: Path, source_evidence: tuple[SourceEvidence, ...], failure: str
) -> None:
    request = REQUEST
    caps = SeedCaps()
    if failure == "tampered-wacz":
        damaged = tmp_path / "damaged.wacz"
        shutil.copyfile(source_evidence[2].wacz, damaged)
        _corrupt(damaged)
        source_evidence = (*source_evidence[:2], replace(source_evidence[2], wacz=damaged))
    elif failure == "missing-response":
        source_evidence = (
            replace(source_evidence[0], raw=tmp_path / "missing.raw"),
            *source_evidence[1:],
        )
    elif failure == "wrong-resource":
        source_evidence = (replace(source_evidence[1], kind="request-json"), *source_evidence[1:])
    elif failure == "wrong-case":
        request = replace(REQUEST, request_id=702)
    elif failure == "missing-attachment":
        source_evidence = source_evidence[:2]
    elif failure == "transfer-byte-cap":
        caps = SeedCaps(max_bytes=100)
    elif failure == "derived-byte-cap":
        # The transferred files fit, but the derived request and attachment sidecar do not.
        caps = SeedCaps(
            max_bytes=sum(
                path.stat().st_size
                for entry in source_evidence
                for path in (entry.raw, entry.result, entry.receipt, entry.wacz, entry.link)
            ),
        )
    data = tmp_path / "data"
    ledger = data / "ledger.jsonl"
    with pytest.raises(CaptureError):
        run_seed(
            requests=[request],
            ledger_path=ledger,
            data_dir=data,
            derived_dir=data / "derived",
            caps=caps,
            dry_run=False,
            capture=partial(capture_offline_evidence, evidence=source_evidence, verifier=rust_cli),
        )
    assert load_ledger(ledger) == set()
    assert _read_rows(ledger)[0]["status"] == "failed"
    assert not (data / "offline-seed" / str(request.request_id)).exists()


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        ("request-id", "filename-safe"),
        ("source-arguments", "does not accept source CLI arguments"),
        ("no-page", "requires request JSON and page evidence"),
        ("unexpected-kind", "unexpected source kind"),
        ("aliased-output", "must not contain symlinks"),
    ],
)
def test_offline_capture_rejects_invalid_setup(
    tmp_path: Path,
    rust_cli: Path,
    source_evidence: tuple[SourceEvidence, ...],
    failure: str,
    message: str,
) -> None:
    request = REQUEST
    extra_args = ()
    data = tmp_path / "data"
    if failure == "request-id":
        request = replace(REQUEST, request_id="../outside")
    elif failure == "source-arguments":
        extra_args = ("--base-url", "https://source.invalid")
    elif failure == "no-page":
        source_evidence = source_evidence[:1]
    elif failure == "unexpected-kind":
        source_evidence = (*source_evidence[:2], source_evidence[1])
    elif failure == "aliased-output":
        data.mkdir()
        (data / "offline-seed").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match=message):
        capture_offline_evidence(
            request,
            data,
            tmp_path / "dist",
            SeedCaps(),
            extra_args,
            evidence=source_evidence,
            verifier=rust_cli,
        )
    assert not (tmp_path / "outside").exists()
    assert not (tmp_path / "701").exists()
    assert not (data / "offline-seed" / "701").exists()


@pytest.mark.parametrize(
    "locator",
    [
        None,
        "file:///fictional/attachment.txt",
        "https://source.invalid/attachments/a.txt?credential=fictional",
        "https://source.invalid/attachments/signed--fictional/a.txt",
    ],
)
def test_offline_capture_rejects_private_or_unsupported_locators(locator: str | None) -> None:
    with pytest.raises(ValueError, match="attachment URL"):
        offline_seed._safe_locator(locator)
