"""Contract checks for the GitHub-only AU-NSW private retention workflow."""

from pathlib import Path


def test_full_au_nsw_workflow_is_sequential_private_hf_retention() -> None:
    workflow = Path(".github/workflows/au_nsw_full_private_hf_capture.yml").read_text(
        encoding="utf-8"
    )
    assert "workflow_dispatch:" in workflow
    assert "max-parallel" not in workflow
    assert "HF_AU_NSW_REPO_ID" in workflow
    assert "I_CONFIRM_FULL_AU_NSW_PRIVATE_HF_CAPTURE" in workflow
    assert "AUTONOMOUS_AU_CAPTURE_ENABLED" in workflow
    assert "requests per resumable tranche" in workflow.lower()
