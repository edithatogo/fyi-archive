from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fyi_archive.archive_package import (
    EvidenceFile,
    PackageInputs,
    build_archive_package,
    verify_archive_package,
    verify_package_store,
)
from fyi_archive.commands.process import app


def _inputs(root: Path) -> PackageInputs:
    root.mkdir()
    for name in ("cases", "events", "attachments", "takedown"):
        (root / f"{name}.ndjson").write_bytes(b"")
    (root / "provenance.json").write_text("{}\n", encoding="utf-8")
    (root / "retention.json").write_text('{"status":"retained"}\n', encoding="utf-8")
    return PackageInputs(
        instance_id="se-handlingar",
        archive_revision=1,
        repository="https://huggingface.co/datasets/example/fictional",
        repository_revision="0123456789abcdef0123456789abcdef01234567",
        cases_path=root / "cases.ndjson",
        events_path=root / "events.ndjson",
        attachments_path=root / "attachments.ndjson",
        takedown_inventory_path=root / "takedown.ndjson",
        provenance_path=root / "provenance.json",
        retention_path=root / "retention.json",
    )


def test_package_retains_exact_named_evidence_and_detects_tampering(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    source = tmp_path / "input.wacz"
    source.write_bytes(b"synthetic binary evidence\x00\xff")
    inputs = replace(
        inputs,
        evidence_files=(EvidenceFile("capture.wacz", source, "application/wacz"),),
    )
    store = tmp_path / "store"
    result = build_archive_package(inputs, store)
    package = store / result["package_path"]
    assert (package / "evidence" / "capture.wacz").read_bytes() == source.read_bytes()
    manifest = json.loads((package / "archive-package.json").read_bytes())
    entry = next(item for item in manifest["files"] if item["path"] == "evidence/capture.wacz")
    assert (entry["role"], entry["media_type"], entry["row_count"]) == (
        "other",
        "application/wacz",
        None,
    )
    assert verify_archive_package(package)["verified"]
    assert verify_package_store(store)["verified"]
    (package / "evidence" / "capture.wacz").write_bytes(b"synthetic binary evidence\x00\xfe")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_archive_package(package)


@pytest.mark.parametrize("name", ["../escape", ".", "a/b", "a\\b", ""])
def test_evidence_names_cannot_escape_package(tmp_path: Path, name: str) -> None:
    inputs = _inputs(tmp_path / "inputs")
    source = tmp_path / "capture"
    source.write_bytes(b"fixture")
    inputs = replace(inputs, evidence_files=(EvidenceFile(name, source, "application/wacz"),))
    with pytest.raises(ValueError, match="evidence"):
        build_archive_package(inputs, tmp_path / "store")


def test_duplicate_and_missing_evidence_fail_closed(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    source = tmp_path / "capture"
    source.write_bytes(b"fixture")
    duplicate = EvidenceFile("capture.wacz", source, "application/wacz")
    with pytest.raises(ValueError, match="duplicate"):
        build_archive_package(
            replace(inputs, evidence_files=(duplicate, duplicate)), tmp_path / "a"
        )
    missing = EvidenceFile("receipt.json", tmp_path / "missing", "application/json")
    with pytest.raises(ValueError, match="evidence"):
        build_archive_package(replace(inputs, evidence_files=(missing,)), tmp_path / "b")


def test_symlinked_evidence_input_fails_closed(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    source = tmp_path / "capture.wacz"
    source.write_bytes(b"fixture")
    link = tmp_path / "link.wacz"
    link.symlink_to(source)
    evidence = EvidenceFile("capture.wacz", link, "application/wacz")
    with pytest.raises(ValueError, match="evidence"):
        build_archive_package(replace(inputs, evidence_files=(evidence,)), tmp_path / "store")


def test_cli_retains_each_evidence_file(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    capture = tmp_path / "capture.wacz"
    receipt = tmp_path / "receipt.json"
    prior_manifest = tmp_path / "archive-package.json"
    capture.write_bytes(b"synthetic WACZ")
    receipt.write_bytes(b"synthetic receipt")
    prior_manifest.write_bytes(b'{"source":"prior-fictional-package"}\n')
    store = tmp_path / "store"
    result = CliRunner().invoke(
        app,
        [
            "package-archive",
            "--instance",
            inputs.instance_id,
            "--archive-revision",
            "1",
            "--repository",
            inputs.repository,
            "--repository-revision",
            inputs.repository_revision,
            "--cases",
            str(inputs.cases_path),
            "--events",
            str(inputs.events_path),
            "--attachments",
            str(inputs.attachments_path),
            "--takedown-inventory",
            str(inputs.takedown_inventory_path),
            "--provenance",
            str(inputs.provenance_path),
            "--retention",
            str(inputs.retention_path),
            "--output-root",
            str(store),
            "--evidence",
            str(capture),
            "--evidence",
            str(receipt),
            "--evidence",
            str(prior_manifest),
        ],
    )
    assert result.exit_code == 0, result.output
    package = store / json.loads(result.output)["package_path"]
    assert (package / "evidence" / "capture.wacz").read_bytes() == capture.read_bytes()
    assert (package / "evidence" / "receipt.json").read_bytes() == receipt.read_bytes()
    assert (package / "evidence" / prior_manifest.name).read_bytes() == prior_manifest.read_bytes()
    assert verify_package_store(store)["verified"]
    undeclared = package / "metadata" / prior_manifest.name
    undeclared.write_bytes(prior_manifest.read_bytes())
    with pytest.raises(ValueError, match="file inventory does not match"):
        verify_archive_package(package)
