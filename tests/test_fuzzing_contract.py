"""Contracts for bounded, least-privilege property and coverage-guided fuzzing."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "fuzz.yml"


def test_fuzz_workflow_is_bounded_pinned_and_least_privilege() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "permissions:\n  contents: read" in workflow
    assert workflow.count("persist-credentials: false") == 3
    assert workflow.count("actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10") == 3
    assert workflow.count("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02") == 2
    assert "timeout-minutes: 6" in workflow
    assert "timeout-minutes: 50" in workflow
    assert "--seconds-per-target 20 --rss-limit-mb 512" in workflow
    assert "retention-days: 14" in workflow
    assert "retention-days: 30" in workflow
    assert workflow.count("fuzz/corpus/") == 2
    assert workflow.count("fuzz/artifacts/") == 2


def test_both_fuzzing_layers_are_required_in_pull_requests() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "Hypothesis property smoke" in workflow
    assert "Run bounded coverage-guided smoke" in workflow
    assert workflow.count("uv run --with atheris==3.1.0") == 2


def test_runner_declares_all_high_risk_targets_and_caps() -> None:
    source = (ROOT / "scripts" / "run_fuzzers.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert tree is not None
    for target in (
        "fuzz_catalog_archive.py",
        "fuzz_archive_package.py",
        "fuzz_historical_manifest.py",
    ):
        assert target in source
    assert "MAX_SECONDS_PER_TARGET = 900" in source
    assert "MAX_RSS_MB = 1024" in source
    assert "MAX_INPUT_BYTES = 64 * 1024" in source
    assert "timeout=args.seconds_per_target + 30" in source


def test_harnesses_instrument_production_modules() -> None:
    expected = {
        "fuzz_catalog_archive.py": "parse_catalog_archive",
        "fuzz_archive_package.py": "verify_archive_package",
        "fuzz_historical_manifest.py": "build_manifest",
    }
    for filename, entrypoint in expected.items():
        source = (ROOT / "fuzz" / filename).read_text(encoding="utf-8")
        assert "atheris.instrument_imports()" in source
        assert entrypoint in source
