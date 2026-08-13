from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import typer
from jsonschema import Draft202012Validator, FormatChecker
from typer.testing import CliRunner

from fyi_archive.archive_package import (
    PackageInputs,
    build_archive_package,
    canonical_json,
    package_id,
    sha256_file,
    verify_archive_package,
    verify_package_store,
)
from fyi_archive.cli import app
from fyi_archive.commands.process import package_archive

REPOSITORY = "https://huggingface.co/datasets/edithatogo/handlingar-archive-se"
REPOSITORY_REVISION = "0123456789abcdef0123456789abcdef01234567"
ABSOLUTE_TEST_PATH = f"{Path.cwd().drive}/absolute.json" if Path.cwd().drive else "/absolute.json"


def _write_json(path: Path, value: object) -> None:
    path.write_bytes(canonical_json(value) + b"\n")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_bytes(b"".join(canonical_json(row) + b"\n" for row in rows))


def _inputs(root: Path, *, revision: int = 1) -> PackageInputs:
    root.mkdir(parents=True)
    cases = root / "cases.ndjson"
    events = root / "events.ndjson"
    attachments = root / "attachments.ndjson"
    takedown = root / "takedown.ndjson"
    provenance = root / "provenance.json"
    retention = root / "retention.json"
    _write_jsonl(cases, [{"case_id": "case-1"}, {"case_id": "case-2"}])
    _write_jsonl(
        events,
        [
            {
                "schema_version": "1.0.0",
                "event_id": "event-1",
                "case_id": "case-1",
                "activity": "opened",
                "position": {"sequence": 1},
            },
            {
                "schema_version": "1.0.0",
                "event_id": "event-2",
                "case_id": "case-2",
                "activity": "closed",
                "position": {"sequence": 2},
            },
        ],
    )
    _write_jsonl(attachments, [{"attachment_id": "attachment-1", "case_id": "case-1"}])
    _write_jsonl(takedown, [{"case_id": "removed-case", "operation": "retract"}])
    _write_json(
        provenance,
        {
            "source": "fyi-cli",
            "source_revision": REPOSITORY_REVISION,
            "transformation": "fyi-archive-package-v1",
        },
    )
    _write_json(retention, {"status": "retained", "policy": "public-archive"})
    return PackageInputs(
        instance_id="se-handlingar",
        archive_revision=revision,
        repository=REPOSITORY,
        repository_revision=REPOSITORY_REVISION,
        cases_path=cases,
        events_path=events,
        attachments_path=attachments,
        takedown_inventory_path=takedown,
        provenance_path=provenance,
        retention_path=retention,
    )


def _package_dir(store: Path, revision: int = 1) -> Path:
    return store / "packages" / "se-handlingar" / f"{revision:020d}"


def _symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except OSError as error:
        pytest.skip(f"symlink creation is unavailable: {error}")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rewrite_manifest(package: Path, mutation: Callable[[dict[str, Any]], None]) -> None:
    path = package / "archive-package.json"
    manifest = _load_json(path)
    mutation(manifest)
    if manifest.get("package_id") != "invalid":
        manifest["package_id"] = package_id(manifest)
    _write_json(path, manifest)


def _rewrite_declared_json(
    package: Path,
    relative: str,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    path = package / relative
    document = _load_json(path)
    mutation(document)
    _write_json(path, document)

    def refresh(manifest: dict[str, Any]) -> None:
        entry = next(row for row in manifest["files"] if row["path"] == relative)
        entry["sha256"] = sha256_file(path)
        entry["byte_count"] = path.stat().st_size

    _rewrite_manifest(package, refresh)


def _build_cli_args(inputs: PackageInputs, store: Path) -> list[str]:
    return [
        "process",
        "package-archive",
        "--instance",
        inputs.instance_id,
        "--archive-revision",
        str(inputs.archive_revision),
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
    ]


def test_snapshot_package_is_deterministic_and_schema_valid(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    first_store = tmp_path / "first"
    second_store = tmp_path / "second"
    first = build_archive_package(inputs, first_store)
    second = build_archive_package(inputs, second_store)

    assert first == second
    first_package = _package_dir(first_store)
    second_package = _package_dir(second_store)
    assert {
        path.relative_to(first_package).as_posix(): path.read_bytes()
        for path in first_package.rglob("*")
        if path.is_file()
    } == {
        path.relative_to(second_package).as_posix(): path.read_bytes()
        for path in second_package.rglob("*")
        if path.is_file()
    }
    manifest = json.loads((first_package / "archive-package.json").read_text(encoding="utf-8"))
    schema = json.loads(Path("schemas/archive-package.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(manifest)
    assert manifest["ordering"] == {
        "event_key": "source_sequence_then_event_id",
        "first_source_sequence": 1,
        "last_source_sequence": 2,
    }
    assert manifest["counts"] == {
        "file_count": 7,
        "case_count": 2,
        "event_count": 2,
        "attachment_count": 1,
    }
    assert manifest["takedown_revision"] == sha256_file(
        first_package / "metadata" / "takedown-inventory.ndjson"
    )
    assert verify_archive_package(first_package)["package_id"] == first["package_id"]
    assert verify_package_store(first_store) == {
        "verified": True,
        "instance_count": 1,
        "package_count": 1,
    }


def test_identical_revision_is_idempotent_but_conflict_fails(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    first = build_archive_package(inputs, store)
    assert build_archive_package(inputs, store) == first
    inputs.events_path.write_bytes(
        inputs.events_path.read_bytes().replace(b'"activity":"closed"', b'"activity":"refused"')
    )
    with pytest.raises(ValueError, match="different immutable package"):
        build_archive_package(inputs, store)


def test_delta_appends_revision_and_updates_atomic_indexes(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    first = build_archive_package(inputs, store)
    delta = replace(
        inputs,
        archive_revision=2,
        package_kind="delta",
        base_archive_revision=1,
    )
    second = build_archive_package(delta, store)
    index = json.loads(
        (store / "indexes" / "se-handlingar" / "index.json").read_text(encoding="utf-8")
    )
    latest = json.loads(
        (store / "indexes" / "se-handlingar" / "latest.json").read_text(encoding="utf-8")
    )
    catalog = json.loads((store / "catalog.json").read_text(encoding="utf-8"))
    assert [row["archive_revision"] for row in index["revisions"]] == [1, 2]
    assert latest["revision"]["package_id"] == second["package_id"]
    assert catalog["instances"] == [
        {
            "index_path": "indexes/se-handlingar/index.json",
            "index_sha256": sha256_file(store / "indexes" / "se-handlingar" / "index.json"),
            "instance_id": "se-handlingar",
            "latest_archive_revision": 2,
            "latest_package_id": second["package_id"],
            "latest_path": "indexes/se-handlingar/latest.json",
            "latest_sha256": sha256_file(store / "indexes" / "se-handlingar" / "latest.json"),
            "revision_count": 2,
        }
    ]
    assert first["package_id"] != second["package_id"]
    assert verify_package_store(store)["package_count"] == 2


def test_delta_requires_latest_base_and_first_revision_snapshot(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    with pytest.raises(ValueError, match=r"first package.*snapshot"):
        build_archive_package(replace(inputs, package_kind="delta", base_archive_revision=1), store)
    build_archive_package(inputs, store)
    with pytest.raises(ValueError, match="must equal the latest"):
        build_archive_package(
            replace(
                inputs,
                archive_revision=2,
                package_kind="delta",
                base_archive_revision=99,
            ),
            store,
        )


def test_package_verification_rejects_tampering_and_unlisted_files(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    build_archive_package(inputs, store)
    package = _package_dir(store)
    (package / "cases.ndjson").write_bytes(b"tampered\n")
    with pytest.raises(ValueError, match=r"byte_count mismatch|checksum mismatch"):
        verify_archive_package(package)

    other_store = tmp_path / "other-store"
    build_archive_package(inputs, other_store)
    other_package = _package_dir(other_store)
    (other_package / "unlisted.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(ValueError, match="inventory does not match"):
        verify_archive_package(other_package)


@pytest.mark.parametrize("link_kind", ["root", "manifest", "declared", "unlisted"])
def test_package_verification_rejects_symlinks(tmp_path: Path, link_kind: str) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    build_archive_package(inputs, store)
    package = _package_dir(store)

    if link_kind == "root":
        link = tmp_path / "package-link"
        _symlink_or_skip(link, package)
        candidate = link
    elif link_kind == "manifest":
        manifest = package / "archive-package.json"
        target = tmp_path / "manifest.json"
        manifest.replace(target)
        _symlink_or_skip(manifest, target)
        candidate = package
    elif link_kind == "declared":
        declared = package / "cases.ndjson"
        target = tmp_path / "cases.ndjson"
        declared.replace(target)
        _symlink_or_skip(declared, target)
        candidate = package
    else:
        target = tmp_path / "unlisted.txt"
        target.write_text("outside", encoding="utf-8")
        _symlink_or_skip(package / "unlisted.txt", target)
        candidate = package

    with pytest.raises(ValueError, match="symlink"):
        verify_archive_package(candidate)


def test_store_verification_rejects_rewritten_index_without_pointer_update(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    build_archive_package(inputs, store)
    index_path = store / "indexes" / "se-handlingar" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["revisions"][0]["counts"]["case_count"] = 99
    _write_json(index_path, index)
    with pytest.raises(ValueError, match="index checksum mismatch"):
        verify_package_store(store)


def test_store_verification_rejects_noncanonical_index_package_path(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    build_archive_package(inputs, store)
    index_path = store / "indexes" / "se-handlingar" / "index.json"
    latest_path = store / "indexes" / "se-handlingar" / "latest.json"
    catalog_path = store / "catalog.json"

    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["revisions"][0]["package_path"] = "packages/se-handlingar/../outside"
    _write_json(index_path, index)
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    latest["index_sha256"] = sha256_file(index_path)
    latest["revision"] = index["revisions"][0]
    _write_json(latest_path, latest)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["instances"][0]["index_sha256"] = sha256_file(index_path)
    catalog["instances"][0]["latest_sha256"] = sha256_file(latest_path)
    _write_json(catalog_path, catalog)

    with pytest.raises(ValueError, match="indexed package_path must equal"):
        verify_package_store(store)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"repository": "https://handlingar.se/archive"}, "source-site"),
        ({"repository_revision": "main"}, "40-character"),
        ({"archive_revision": 0}, "positive"),
    ],
)
def test_identity_inputs_fail_closed(
    tmp_path: Path, mutation: dict[str, object], message: str
) -> None:
    inputs = _inputs(tmp_path / "inputs")
    with pytest.raises(ValueError, match=message):
        build_archive_package(replace(inputs, **mutation), tmp_path / "store")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"repository": "http://archive.example/data"}, "HTTPS archive"),
        ({"repository": "https://user@example.test/data"}, "HTTPS archive"),
        ({"base_archive_revision": 1}, "snapshot packages"),
        ({"package_kind": "delta", "base_archive_revision": 0}, "positive base"),
        ({"package_kind": "invalid"}, "snapshot or delta"),
    ],
)
def test_additional_package_input_errors(
    tmp_path: Path, mutation: dict[str, object], message: str
) -> None:
    inputs = _inputs(tmp_path / "inputs")
    with pytest.raises(ValueError, match=message):
        build_archive_package(replace(inputs, **mutation), tmp_path / "store")


@pytest.mark.parametrize(
    ("target", "contents", "message"),
    [
        ("provenance", "[]\n", "JSON object"),
        ("cases", "{bad json}\n", "invalid cases JSON"),
        ("cases", "[]\n", "must be a JSON object"),
        ("events", '{"position":{"sequence":1}}\n', "requires event_id"),
        ("events", '{"event_id":"event","source_sequence":false}\n', "source sequence"),
    ],
)
def test_malformed_package_inputs_fail_closed(
    tmp_path: Path, target: str, contents: str, message: str
) -> None:
    inputs = _inputs(tmp_path / "inputs")
    path = getattr(inputs, f"{target}_path")
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        build_archive_package(inputs, tmp_path / "store")


def test_missing_and_empty_ndjson_inputs_are_handled(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "missing-inputs")
    inputs.cases_path.unlink()
    with pytest.raises(ValueError, match="missing cases file"):
        build_archive_package(inputs, tmp_path / "missing-store")

    inputs = _inputs(tmp_path / "empty-inputs")
    inputs.events_path.write_text("\n", encoding="utf-8")
    result = build_archive_package(inputs, tmp_path / "empty-store")
    manifest = _load_json(
        tmp_path / "empty-store" / result["package_path"] / "archive-package.json"
    )
    assert manifest["ordering"]["first_source_sequence"] is None
    assert manifest["ordering"]["last_source_sequence"] is None


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update(schema_version="2.0.0"), "schema_version"),
        (lambda value: value.update(instance_id=None), "instance_id"),
        (lambda value: value.update(archive_revision="1"), "positive integer"),
        (lambda value: value.update(archive_revision=0), "positive integer"),
        (lambda value: value.update(source=[]), "source must be an object"),
        (
            lambda value: value.update(source={"repository": None, "revision": None}),
            "repository and revision",
        ),
        (lambda value: value.update(package_id="invalid"), "package_id"),
        (lambda value: value.update(files=[]), "non-empty array"),
        (lambda value: value["files"][0].update(order=2), "order must be"),
        (
            lambda value: value["files"][1].update(path=value["files"][0]["path"]),
            "paths must be unique",
        ),
        (lambda value: value["counts"].update(file_count=99), "file_count mismatch"),
        (lambda value: value["counts"].update(case_count=99), "role counts"),
        (
            lambda value: value["ordering"].update(last_source_sequence=99),
            "ordering bounds",
        ),
    ],
)
def test_manifest_validation_errors(
    tmp_path: Path,
    mutation: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    build_archive_package(inputs, store)
    package = _package_dir(store)
    _rewrite_manifest(package, mutation)
    with pytest.raises((TypeError, ValueError), match=message):
        verify_archive_package(package)


@pytest.mark.parametrize(
    ("entry_mutation", "message"),
    [
        (lambda entry: entry.update(row_count=1), "must not declare row_count"),
        (lambda entry: entry.update(role="unsupported"), "unsupported package file role"),
        (lambda entry: entry.update(media_type="application/json"), "must be NDJSON"),
        (lambda entry: entry.update(row_count=99), "row_count mismatch"),
    ],
)
def test_declared_file_metadata_errors(
    tmp_path: Path,
    entry_mutation: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    build_archive_package(inputs, store)
    package = _package_dir(store)

    def mutate(manifest: dict[str, Any]) -> None:
        role = "other" if "row_count" in message and "not declare" in message else "cases"
        entry = next(row for row in manifest["files"] if row["role"] == role)
        entry_mutation(entry)

    _rewrite_manifest(package, mutate)
    with pytest.raises(ValueError, match=message):
        verify_archive_package(package)


@pytest.mark.parametrize(
    ("path_value", "message"),
    [
        (None, "relative POSIX path"),
        (r"metadata\provenance.json", "relative POSIX path"),
        ("../outside.json", "escapes the package root"),
        (ABSOLUTE_TEST_PATH, "escapes the package root"),
    ],
)
def test_declared_file_paths_must_be_safe_and_relative(
    tmp_path: Path, path_value: object, message: str
) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    build_archive_package(inputs, store)
    package = _package_dir(store)

    def mutate(manifest: dict[str, Any]) -> None:
        manifest["files"][0]["path"] = path_value

    _rewrite_manifest(package, mutate)
    with pytest.raises(ValueError, match=message):
        verify_archive_package(package)


def test_same_size_file_tampering_reaches_checksum_validation(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    build_archive_package(inputs, store)
    package = _package_dir(store)
    path = package / "cases.ndjson"
    path.write_bytes(path.read_bytes().replace(b"case-1", b"case-x"))
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_archive_package(package)


def test_manifest_identity_corruption_is_rejected(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    build_archive_package(inputs, store)
    manifest_path = _package_dir(store) / "archive-package.json"
    manifest = _load_json(manifest_path)
    manifest["package_id"] = "0" * 64
    _write_json(manifest_path, manifest)
    with pytest.raises(ValueError, match="identity mismatch"):
        verify_archive_package(_package_dir(store))


@pytest.mark.parametrize(
    ("relative", "mutation", "message"),
    [
        (
            "metadata/package-metadata.json",
            lambda value: value.update(schema="unknown"),
            "metadata schema",
        ),
        (
            "metadata/package-metadata.json",
            lambda value: value.update(archive_revision=99),
            "metadata archive revision",
        ),
        (
            "metadata/package-metadata.json",
            lambda value: value.update(takedown_revision="0" * 64),
            "metadata takedown revision",
        ),
        (
            "metadata/package-metadata.json",
            lambda value: value.update(base_archive_revision=1),
            "snapshot package metadata",
        ),
        (
            "metadata/package-metadata.json",
            lambda value: value.update(package_kind="delta", base_archive_revision=1),
            "delta package metadata",
        ),
        (
            "metadata/package-metadata.json",
            lambda value: value.update(package_kind="unknown"),
            "metadata kind",
        ),
        (
            "metadata/provenance.json",
            lambda value: value.update(source="other"),
            "provenance metadata",
        ),
        (
            "metadata/retention.json",
            lambda value: value.update(policy="other"),
            "retention metadata does not reconcile",
        ),
        (
            "metadata/package-metadata.json",
            lambda value: value.update(compatible_contracts={}),
            "compatibility contracts",
        ),
    ],
)
def test_sidecar_reconciliation_errors(
    tmp_path: Path,
    relative: str,
    mutation: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    build_archive_package(inputs, store)
    package = _package_dir(store)
    _rewrite_declared_json(package, relative, mutation)
    with pytest.raises(ValueError, match=message):
        verify_archive_package(package)


def test_takedown_digest_must_match_inventory(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    build_archive_package(inputs, store)
    package = _package_dir(store)
    path = package / "metadata" / "takedown-inventory.ndjson"
    path.write_bytes(path.read_bytes().replace(b"retract", b"replace"))

    def refresh_file_only(manifest: dict[str, Any]) -> None:
        entry = next(row for row in manifest["files"] if row["path"].endswith("inventory.ndjson"))
        entry["sha256"] = sha256_file(path)
        entry["byte_count"] = path.stat().st_size

    _rewrite_manifest(package, refresh_file_only)
    with pytest.raises(ValueError, match="takedown revision"):
        verify_archive_package(package)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "2.0.0", "index schema_version"),
        ("instance_id", "ua-dostup", "index instance mismatch"),
        ("revisions", {}, "revisions must be an array"),
    ],
)
def test_existing_index_shape_errors(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    build_archive_package(inputs, store)
    index_path = store / "indexes" / inputs.instance_id / "index.json"
    index = _load_json(index_path)
    index[field] = value
    _write_json(index_path, index)
    with pytest.raises(ValueError, match=message):
        build_archive_package(inputs, store)


def test_conflicting_index_entry_and_catalog_schema_fail_closed(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    build_archive_package(inputs, store)
    index_path = store / "indexes" / inputs.instance_id / "index.json"
    index = _load_json(index_path)
    index["revisions"][0]["counts"]["case_count"] = 99
    _write_json(index_path, index)
    with pytest.raises(ValueError, match="indexes a different package"):
        build_archive_package(inputs, store)

    clean_store = tmp_path / "catalog-store"
    build_archive_package(inputs, clean_store)
    catalog_path = clean_store / "catalog.json"
    catalog = _load_json(catalog_path)
    catalog["schema_version"] = "2.0.0"
    _write_json(catalog_path, catalog)
    with pytest.raises(ValueError, match="catalog schema_version"):
        build_archive_package(replace(inputs, archive_revision=2), clean_store)


def test_event_order_and_retention_are_required(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    rows = inputs.events_path.read_text(encoding="utf-8").splitlines()
    inputs.events_path.write_text("\n".join(reversed(rows)) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="strictly ordered"):
        build_archive_package(inputs, tmp_path / "unordered")

    inputs = _inputs(tmp_path / "fresh-inputs")
    _write_json(inputs.retention_path, {"policy": "missing-status"})
    with pytest.raises(ValueError, match="retention metadata requires"):
        build_archive_package(inputs, tmp_path / "missing-retention")


def test_cli_builds_and_verifies_store_without_tokens(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    runner = CliRunner()
    result = runner.invoke(app, _build_cli_args(inputs, store))
    assert result.exit_code == 0, result.output
    package = runner.invoke(
        app,
        [
            "process",
            "verify-archive-package",
            "--package-dir",
            str(_package_dir(store)),
        ],
    )
    assert package.exit_code == 0, package.output
    assert json.loads(package.output)["verified"] is True
    verified = runner.invoke(
        app,
        ["process", "verify-archive-package-store", "--output-root", str(store)],
    )
    assert verified.exit_code == 0, verified.output
    assert json.loads(verified.output)["package_count"] == 1


def test_archive_package_cli_errors_are_operator_facing(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path / "inputs")
    store = tmp_path / "store"
    runner = CliRunner()

    invalid_kind = runner.invoke(
        app,
        [*_build_cli_args(inputs, store), "--package-kind", "invalid"],
    )
    assert invalid_kind.exit_code == 2
    with pytest.raises(typer.BadParameter, match="package-kind must be snapshot or delta"):
        package_archive(
            instance=inputs.instance_id,
            archive_revision=inputs.archive_revision,
            repository=inputs.repository,
            repository_revision=inputs.repository_revision,
            cases=inputs.cases_path,
            events=inputs.events_path,
            attachments=inputs.attachments_path,
            takedown_inventory=inputs.takedown_inventory_path,
            provenance=inputs.provenance_path,
            retention=inputs.retention_path,
            output_root=store,
            package_kind="invalid",
            base_archive_revision=None,
        )

    invalid_source = runner.invoke(
        app,
        _build_cli_args(replace(inputs, repository="http://archive.example/data"), store),
    )
    assert invalid_source.exit_code == 2
    assert "HTTPS archive transport URI" in invalid_source.output

    invalid_package = runner.invoke(
        app,
        [
            "process",
            "verify-archive-package",
            "--package-dir",
            str(tmp_path / "missing-package"),
        ],
    )
    assert invalid_package.exit_code == 2
    assert "archive-package.json" in invalid_package.output

    invalid_store = runner.invoke(
        app,
        [
            "process",
            "verify-archive-package-store",
            "--output-root",
            str(tmp_path / "missing-store"),
        ],
    )
    assert invalid_store.exit_code == 2
    assert "catalog.json" in invalid_store.output
