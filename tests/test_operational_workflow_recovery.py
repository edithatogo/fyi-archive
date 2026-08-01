"""Regression contracts for hosted workflow recovery paths."""

from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_alaveteli_core_normalizes_cdx_error_objects() -> None:
    workflow = (ROOT / ".github/workflows/alaveteli_historical_core.yml").read_text(
        encoding="utf-8"
    )

    assert "cdx-error.json" in workflow
    assert "invalid_response" in workflow
    assert "printf '[]\\n'" in workflow
    assert '"schema":"historical-source-index-v1"' not in workflow


def test_project_sync_uses_bounded_credential_fallback() -> None:
    workflow = (ROOT / ".github/workflows/project_sync.yml").read_text(encoding="utf-8")

    assert "secrets.RIOPA_PROJECT_TOKEN || secrets.WORKFLOW_PAT" in workflow
