from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github/workflows/historical_source_indexes.yml"


def test_morph_workflow_uses_secret_and_retains_redacted_provenance() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "MORPH_API_KEY: ${{ secrets.MORPH_API_KEY }}" in workflow
    assert '"key=${MORPH_API_KEY}"' in workflow
    assert '"secret_values_recorded": False' in workflow
