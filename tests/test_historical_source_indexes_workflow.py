from pathlib import Path

ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github/workflows/historical_source_indexes.yml"


def test_morph_workflow_uses_secret_and_retains_redacted_provenance() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "MORPH_API_KEY: ${{ secrets.MORPH_API_KEY }}" in workflow
    assert '"key=${MORPH_API_KEY}"' in workflow
    assert '"secret_values_recorded": False' in workflow
    assert '"url=www.righttoknow.org.au/request"' in workflow
    assert '"url=www.righttoknow.org.au/request/*"' not in workflow


def test_all_instance_workflow_is_bounded_and_uses_registry_prefix_queries() -> None:
    workflow = (ROOT / ".github/workflows/all_instance_historical_indexes.yml").read_text(
        encoding="utf-8"
    )
    assert "from fyi_archive.instances import list_instances" in workflow
    assert "CDX_LIMIT_PER_INSTANCE" in workflow
    assert "between 1 and 100000" in workflow
    assert '"url=${host}/request"' in workflow
    assert "request/*" not in workflow
    assert "sha256" in workflow
