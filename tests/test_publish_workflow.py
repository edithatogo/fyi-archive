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
