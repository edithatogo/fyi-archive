from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer

from fyi_archive.commands.process import validate_derived
from fyi_archive.derived_layer import validate_derived_manifest

FIXTURE = Path("tests/fixtures/foi_o_extraction_contract_nz.json")


def test_pinned_candidate_contract_is_accepted() -> None:
    result = validate_derived_manifest(json.loads(FIXTURE.read_text(encoding="utf-8")))
    assert result["ok"] is True


def test_mutable_source_revision_is_rejected() -> None:
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    document["provenance"]["source_revision"] = "main"
    result = validate_derived_manifest(document)
    assert result["ok"] is False
    assert "immutable" in result["errors"][-1]


def test_missing_run_provenance_is_rejected() -> None:
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del document["provenance"]["extraction_run_id"]
    result = validate_derived_manifest(document)
    assert result["ok"] is False
    assert "extraction_run_id" in " ".join(result["errors"])


@pytest.mark.parametrize("field", ["message_body", "ocr_text", "embedding_vector", "attachment_bytes"])
def test_raw_material_is_rejected_from_derived_manifest(field: str) -> None:
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    document[field] = "raw-material"
    result = validate_derived_manifest(document)
    assert result["ok"] is False
    assert field in " ".join(result["errors"])


def test_contract_id_is_required_by_validator() -> None:
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    document.pop("contract_id")

    result = validate_derived_manifest(document)

    assert result["ok"] is False
    assert "contract_id" in " ".join(result["errors"])


def test_validate_derived_command_accepts_fixture(tmp_path: Path, capsys) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    validate_derived(manifest=manifest)
    assert '"ok": true' in capsys.readouterr().out


def test_validate_derived_command_rejects_invalid_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    document["release_status"] = "published"
    manifest.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(typer.Exit):
        validate_derived(manifest=manifest)


def test_validate_derived_command_rejects_non_object_and_bad_json(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("[]", encoding="utf-8")
    with pytest.raises(typer.BadParameter, match="JSON object"):
        validate_derived(manifest=manifest)
    manifest.write_text("{", encoding="utf-8")
    with pytest.raises(typer.BadParameter, match="Expecting"):
        validate_derived(manifest=manifest)
