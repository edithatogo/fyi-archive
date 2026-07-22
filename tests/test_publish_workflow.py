"""Contracts for safe publication workflow modes."""

from pathlib import Path


def test_seed_dry_run_skips_live_request_discovery() -> None:
    workflow = Path(".github/workflows/publish_archives.yml").read_text(encoding="utf-8")
    dry_run_guard = 'if [ "$SEED_DRY_RUN" = "true" ]; then'
    assert dry_run_guard in workflow
    guard_start = workflow.index(dry_run_guard)
    discovery_start = workflow.index("uv run fyi discover", guard_start)
    assert workflow.index("else", guard_start) < discovery_start
    assert "Seed dry-run requested; skipping live request discovery" in workflow


def test_publication_dry_run_skips_remote_backfill_verification() -> None:
    workflow = Path(".github/workflows/publish_archives.yml").read_text(encoding="utf-8")
    assert "name: Build deterministic dry-run verification report" in workflow
    assert "if: env.DRY_RUN == 'true'" in workflow
    assert "name: Build backfill verification report" in workflow
    assert "if: env.DRY_RUN != 'true'" in workflow
    assert '"remote_reads": False' in workflow


def test_merge_workflow_rejects_empty_process_event_merge() -> None:
    workflow = Path(".github/workflows/merge_backfill_artifacts.yml").read_text(
        encoding="utf-8"
    )
    assert "refusing to create a verified projection" in workflow
    assert "No process event rows were found; materializing an empty verified projection" not in workflow


def test_merge_workflow_carries_attachment_rows_into_projection() -> None:
    workflow = Path(".github/workflows/merge_backfill_artifacts.yml").read_text(
        encoding="utf-8"
    )
    assert "-name attachments.jsonl" in workflow
    assert "--attachments dist/process-events/attachments.jsonl" in workflow
