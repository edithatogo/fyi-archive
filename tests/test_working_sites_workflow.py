from pathlib import Path

WORKFLOW = Path(".github/workflows/alaveteli_working_sites.yml").read_text(encoding="utf-8")


def test_request_discovery_uses_checkpointed_feed_before_bounded_fallback() -> None:
    discovery = WORKFLOW[WORKFLOW.index("Discover next request queue page") :]
    assert "Prepare resumable request queue" in WORKFLOW
    assert "steps.queue.outputs.pending == '0'" in discovery
    assert "--checkpoint" in discovery
    assert "--max-pages \"$DISCOVERY_MAX_PAGES\"" in discovery
    assert "--backfill-ids" in discovery
    assert "manage_alaveteli_queue.py" in discovery


def test_live_manifest_reads_fyi_cli_raw_request_tree() -> None:
    manifest = WORKFLOW[WORKFLOW.index("Build manifest") :]
    assert 'if [ "$DRY_RUN" != "true" ]; then' in manifest
    assert 'derived="$root/raw/requests"' in manifest


def test_explicit_live_capture_fails_when_ledger_or_manifest_is_empty() -> None:
    verification = WORKFLOW[WORKFLOW.index("Verify explicit live capture") :]
    assert 'entry.get("status") != "completed"' in verification
    assert "record_count < 1" in verification
    assert "inputs.request_ref != ''" in verification


def test_workflow_restores_only_verified_live_state() -> None:
    restore = WORKFLOW[WORKFLOW.index("Restore latest verified site state") :]
    assert "gh run list" in restore
    assert "gh run download" in restore
    assert '"status": "completed"' in restore
    assert '"dry_run": false' in restore
    assert "find \"$candidate\" -type f -path '*/_state/ledger.jsonl'" in restore
    assert 'cp -a "$site_root/." "$root/"' in restore
