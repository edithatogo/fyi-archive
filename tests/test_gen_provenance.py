"""Tests for release provenance generation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import cast


def load_gen_provenance() -> ModuleType:
    module_path = Path("scripts/gen_provenance.py")
    spec = importlib.util.spec_from_file_location("gen_provenance", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_provenance_hashes_lockfile_and_artifacts(tmp_path, monkeypatch) -> None:
    module = load_gen_provenance()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    monkeypatch.setenv("GITHUB_WORKFLOW", "Release")

    Path("uv.lock").write_text("lock-data\n", encoding="utf-8")
    dist = Path("dist")
    dist.mkdir()
    artifact = dist / "sample.wacz"
    artifact.write_text("archive-bytes\n", encoding="utf-8")

    provenance = module.build_provenance(
        artifact_patterns=[artifact.as_posix()],
        output_path=dist / "provenance.json",
        fetch_start="2026-01-01",
        fetch_end="2026-02-01",
        fetch_label="smoke-window",
    )

    artifacts = cast("list[dict[str, object]]", provenance["artifacts"])
    lockfile = cast("dict[str, object]", provenance["lockfile"])
    fetch_window = cast("dict[str, object]", provenance["fetch_window"])
    environment = cast("dict[str, object]", provenance["environment"])

    assert artifacts == [
        {
            "path": "dist/sample.wacz",
            "size_bytes": artifact.stat().st_size,
            "sha256": module.sha256_file(artifact),
        },
    ]
    assert lockfile["sha256"] == module.sha256_file(Path("uv.lock"))
    assert fetch_window["label"] == "smoke-window"
    assert environment["runner"] == "123"


def test_expand_artifact_patterns_excludes_output_file(tmp_path, monkeypatch) -> None:
    module = load_gen_provenance()
    monkeypatch.chdir(tmp_path)
    dist = Path("dist")
    dist.mkdir()
    (dist / "sbom.cdx.json").write_text("{}", encoding="utf-8")
    output_path = dist / "provenance.json"
    output_path.write_text("stale", encoding="utf-8")

    artifacts = module.expand_artifact_patterns(["dist/*.json"], output_path)

    assert artifacts == [dist / "sbom.cdx.json"]
