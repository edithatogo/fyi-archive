from __future__ import annotations

import json
from pathlib import Path

import pytest

from fyi_archive.derived_publication import (
    BUNDLE_SCHEMA,
    package_derived_layer,
    verify_derived_bundle,
)

FIXTURE = Path("tests/fixtures/foi_o_extraction_contract_nz.json")


def _write_candidates(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )


def test_derived_bundle_dry_run_round_trip_and_delta(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    baseline = tmp_path / "baseline.ndjson"
    current = tmp_path / "current.ndjson"
    _write_candidates(
        baseline,
        [
            {"candidate_id": "kept", "label": "request"},
            {"candidate_id": "removed", "label": "decision"},
        ],
    )
    _write_candidates(
        current,
        [
            {"candidate_id": "added", "label": "review"},
            {"candidate_id": "kept", "label": "decision"},
        ],
    )

    output = tmp_path / "bundle"
    bundle = package_derived_layer(
        manifest_path=manifest,
        candidates_path=current,
        output_dir=output,
        baseline_path=baseline,
    )

    assert bundle["publication_status"] == "not_published"
    assert bundle["baseline_delta"] == {
        "baseline_count": 2,
        "current_count": 2,
        "added": ["added"],
        "removed": ["removed"],
        "changed": ["kept"],
    }
    assert verify_derived_bundle(output) == {
        "verified": True,
        "record_count": 2,
        "publication_status": "not_published",
    }


def test_derived_bundle_rejects_raw_material_and_tampering(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    candidates = tmp_path / "candidates.ndjson"
    _write_candidates(candidates, [{"candidate_id": "one", "message_body": "private"}])
    with pytest.raises(ValueError, match="forbidden raw fields"):
        package_derived_layer(
            manifest_path=manifest, candidates_path=candidates, output_dir=tmp_path / "bundle"
        )

    _write_candidates(candidates, [{"candidate_id": "one", "label": "request"}])
    output = tmp_path / "bundle"
    package_derived_layer(manifest_path=manifest, candidates_path=candidates, output_dir=output)
    (output / "candidates.ndjson").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch"):
        verify_derived_bundle(output)


def test_derived_bundle_requires_draft_manifest(tmp_path: Path) -> None:
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    document["release_status"] = "verified"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(document), encoding="utf-8")
    candidates = tmp_path / "candidates.ndjson"
    _write_candidates(candidates, [{"candidate_id": "one"}])
    with pytest.raises(ValueError, match="release_status=draft"):
        package_derived_layer(
            manifest_path=manifest, candidates_path=candidates, output_dir=tmp_path / "bundle"
        )


def test_candidate_input_requires_objects_unique_ids_and_json_object_manifest(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    candidates = tmp_path / "candidates.ndjson"
    manifest.write_text("[]", encoding="utf-8")
    candidates.write_text('{"candidate_id":"one"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        package_derived_layer(
            manifest_path=manifest, candidates_path=candidates, output_dir=tmp_path / "bundle"
        )

    manifest.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    candidates.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain a JSON object"):
        package_derived_layer(
            manifest_path=manifest, candidates_path=candidates, output_dir=tmp_path / "bundle"
        )
    candidates.write_text('{"label":"missing"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="requires candidate_id"):
        package_derived_layer(
            manifest_path=manifest, candidates_path=candidates, output_dir=tmp_path / "bundle"
        )
    candidates.write_text(
        '{"candidate_id":"duplicate"}\n{"candidate_id":"duplicate"}\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="duplicate candidate_id"):
        package_derived_layer(
            manifest_path=manifest, candidates_path=candidates, output_dir=tmp_path / "bundle"
        )


def test_bundle_verifier_reports_schema_artifact_and_count_failures(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    candidates = tmp_path / "candidates.ndjson"
    _write_candidates(candidates, [{"candidate_id": "one"}])

    output = tmp_path / "bundle"
    package_derived_layer(manifest_path=manifest, candidates_path=candidates, output_dir=output)
    bundle_path = output / "bundle-manifest.json"
    original = json.loads(bundle_path.read_text(encoding="utf-8"))

    changed = {**original, "schema": "wrong"}
    bundle_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="bundle schema"):
        verify_derived_bundle(output)

    changed = {**original, "publication_status": "published"}
    bundle_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="publication_status"):
        verify_derived_bundle(output)

    changed = {**original, "artifacts": []}
    bundle_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty"):
        verify_derived_bundle(output)

    changed = {**original, "artifacts": ["bad"]}
    bundle_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="must be an object"):
        verify_derived_bundle(output)

    changed = {**original, "record_count": 2}
    bundle_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="candidate count"):
        verify_derived_bundle(output)

    bundle_path.write_text(json.dumps(original), encoding="utf-8")
    (output / "candidates.ndjson").unlink()
    with pytest.raises(ValueError, match="artifact is missing"):
        verify_derived_bundle(output)


def test_bundle_verifier_rejects_artifact_paths_outside_bundle(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    output.mkdir()
    (output / "bundle-manifest.json").write_text(
        json.dumps({
            "schema": BUNDLE_SCHEMA,
            "publication_status": "not_published",
            "artifacts": [
                {
                    "path": "../outside.ndjson",
                    "sha256": "0" * 64,
                    "bytes": 0,
                }
            ],
        }),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="expected local files"):
        verify_derived_bundle(output)
