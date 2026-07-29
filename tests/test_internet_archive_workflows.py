from pathlib import Path

WORKFLOWS = Path(".github/workflows")


def test_scheduled_indexes_are_explicitly_url_level_only() -> None:
    workflow = (WORKFLOWS / "alaveteli_historical_indexes.yml").read_text(encoding="utf-8")

    assert "CAPTURE_MODE: ${{ matrix.capture_mode }}" in workflow
    assert '--capture-mode "$CAPTURE_MODE"' in workflow
    assert "schedule:" in workflow


def test_all_capture_export_is_scheduled_bounded_and_does_not_replay() -> None:
    workflow = (WORKFLOWS / "alaveteli_historical_all_captures.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow
    assert "EXPORT_ALL_CAPTURE_METADATA" not in workflow
    assert "--capture-mode all_captures" in workflow
    assert "import_historical_sources.py" not in workflow
    assert "if: always()" in workflow
    assert "resume_run_id:" in workflow
    assert "Restore prior page checkpoint" in workflow
    assert "actions: read" in workflow


def test_historical_source_index_uses_fail_closed_paginator() -> None:
    workflow = (WORKFLOWS / "historical_source_indexes.yml").read_text(encoding="utf-8")

    assert "fetch_complete_internet_archive_cdx.py" in workflow
    assert "--capture-mode url_index" in workflow
    assert "internet_archive_retrieval.json" in workflow


def test_separate_site_workflow_auto_restores_latest_checkpoint() -> None:
    workflow = (WORKFLOWS / "foi_site_internet_archive.yml").read_text(encoding="utf-8")

    assert "Resolve prior site checkpoint" in workflow
    assert "REQUESTED_RESUME_RUN_ID" in workflow
    assert "gh run list" in workflow
    assert "gh run download" in workflow
    assert "explicit-resume-run" in workflow
    assert "latest-compatible-checkpoint" in workflow
    assert "RESUME_SOURCE_RUN_ID" in workflow
    assert "--resume-source-run-id" in workflow
    assert "actions: read" in workflow
    assert "max-parallel: 2" in workflow
    assert "MAX_RUNTIME_SECONDS: ${{ inputs.max_runtime_seconds || '1800' }}" in workflow
    assert "MAX_STALL_SECONDS: ${{ inputs.max_stall_seconds || '900' }}" in workflow
    assert '"--max-stall-seconds", os.environ["MAX_STALL_SECONDS"]' in workflow
    assert 'test "$MAX_STALL_SECONDS" -le "$MAX_RUNTIME_SECONDS"' in workflow
    assert "timeout-minutes: 135" in workflow
    assert 'test "$MAX_RUNTIME_SECONDS" -ge 30 && test "$MAX_RUNTIME_SECONDS" -le 7200' in workflow
    assert 'if [ "$MAX_RUNTIME_SECONDS" -gt 2400 ]; then' in workflow
    assert 'test -n "${TARGET_SITE_ID}${TARGET_SITE_IDS}"' in workflow
    assert "site_ids:" in workflow
    assert "TARGET_SITE_IDS" in workflow
    assert "site_ids=site_ids if raw_site_ids else None" in workflow
    assert "max-parallel: 2" in workflow
    assert '"event": "cdx-heartbeat"' in workflow
    assert "process.wait(timeout=60)" in workflow
    assert 'p.get("capture_mode") == sys.argv[2]' in workflow
    assert 'p.get("complete") is True' in workflow
    assert "latest-complete-refresh" in workflow
    assert 'grep -qx "complete=true"' in workflow
    assert 'p.get("pagination", {}).get("mode") == "resume_key"' in workflow
    assert 'grep -qx "pagination-match=true"' in workflow
    assert '"mode": "resume_key"' in workflow
    assert '"continuation": "showResumeKey/resumeKey"' in workflow
    python_close = workflow.index('\' "$manifest" "$CAPTURE_MODE")"')
    pagination_print = workflow.index('print("pagination-match="')
    capture_guard = workflow.index('grep -qx "capture-match=true"')
    pagination_guard = workflow.index('grep -qx "pagination-match=true"')
    complete_guard = workflow.index('if grep -qx "complete=true"')
    artifact_manifest = workflow.index("artifact = {")
    top_level_manifest = workflow.index("manifest = {")
    pagination_manifest = workflow.index('"pagination": {')
    assert pagination_print < python_close
    assert capture_guard < pagination_guard < complete_guard
    assert artifact_manifest < top_level_manifest < pagination_manifest
