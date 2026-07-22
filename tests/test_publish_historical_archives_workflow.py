from pathlib import Path


def test_historical_publication_is_confirmation_gated() -> None:
    workflow = Path('.github/workflows/publish_historical_archives.yml').read_text()
    assert 'publish-historical-archives' in workflow
    assert "env.PUBLISH_TO_HUGGINGFACE == 'true'" in workflow
    assert 'HF_TOKEN is required' in workflow


def test_historical_publication_downloads_run_bound_artifact() -> None:
    workflow = Path('.github/workflows/publish_historical_archives.yml').read_text()
    assert 'run-id: ${{ inputs.historical_run_id }}' in workflow
    assert 'all-instance-internet-archive-cdx-${{ inputs.historical_run_id }}' in workflow
