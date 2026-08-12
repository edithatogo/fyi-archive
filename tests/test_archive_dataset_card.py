"""Tests for the reproducible Hugging Face archive catalog."""

from __future__ import annotations

from pathlib import Path

from fyi_archive.archive_dataset_card import collection_note, render_instance_card
from fyi_archive.instances import get_instance
from scripts.ensure_huggingface_archive_catalog import ordered_instances, plan


def test_historical_card_is_fail_closed_and_instance_specific() -> None:
    instance = get_instance("fr-madada")
    card = render_instance_card(instance)
    assert "license: other" in card
    assert "language:\n  - fr" in card
    assert "task_categories:\n  - text-retrieval" in card
    assert "annotations_creators:\n  - no-annotation" in card
    assert "source_datasets:\n  - other" in card
    assert instance.source in card
    assert instance.hf_repo_id in card
    assert "does not claim records, completeness, or live-API coverage" in card
    assert "list_repo_files" in card
    assert "manifest.schema.json" in card
    assert "license: mit" not in card


def test_collection_note_exposes_status_without_claiming_completion() -> None:
    note = collection_note(get_instance("uk-wdtk"))
    assert "GB | experimental" in note
    assert "complete" not in note.lower()


def test_catalog_plan_contains_every_registered_dataset_once() -> None:
    catalog = plan()
    datasets = catalog["datasets"]
    repo_ids = [item["repo_id"] for item in datasets]
    assert len(repo_ids) == 23
    assert len(set(repo_ids)) == 23
    assert "edithatogo/fyi-archive-nz" in repo_ids
    assert catalog["collection"]["private"] is False


def test_catalog_orders_supported_before_experimental_and_historical() -> None:
    statuses = [item.status for item in ordered_instances()]
    assert statuses[0] == "supported"
    assert statuses.index("historical-only") > statuses.index("experimental")


def test_hf_sync_passes_selected_instance_to_card_renderer() -> None:
    workflow = Path(".github/workflows/hf_sync.yml").read_text(encoding="utf-8")
    assert '--instance "$INSTANCE"' in workflow
    assert "group: hf-sync-${{ inputs.instance || 'nz-fyi' }}" in workflow
    assert "INSTANCE: ${{ inputs.instance || 'nz-fyi' }}" in workflow
    assert 'if [ "$INSTANCE" = "nz-fyi" ]' in workflow
    assert "get_instance(os.environ[\"INSTANCE\"]).hf_repo_id" in workflow
