from pathlib import Path

WORKFLOWS = Path(".github/workflows")


def test_global_wayback_workflow_is_complete_and_provenance_first() -> None:
    workflow = (WORKFLOWS / "foi_site_internet_archive.yml").read_text(encoding="utf-8")

    assert "build_archive_source_graph.py --check" in workflow
    assert "fetch_complete_internet_archive_cdx.py" in workflow
    assert "Fail closed on incomplete snapshot" in workflow
    assert "if: always()" in workflow
    assert "include-hidden-files: true" in workflow
    assert "origin_contacted" in workflow
    assert "durable_handoff" in workflow


def test_read_only_all_capture_export_is_scheduled_and_bounded() -> None:
    workflow = (WORKFLOWS / "alaveteli_historical_all_captures.yml").read_text(encoding="utf-8")

    assert "schedule:" in workflow
    assert "confirm:" not in workflow
    assert "EXPORT_ALL_CAPTURE_METADATA" not in workflow
    assert "--capture-mode all_captures" in workflow
    assert "--max-pages" in workflow
    assert "--max-runtime-seconds" in workflow


def test_live_capture_uses_repository_readiness_not_dispatch_prompts() -> None:
    alaveteli = (WORKFLOWS / "alaveteli_working_sites.yml").read_text(encoding="utf-8")
    assert "live_confirmation:" not in alaveteli
    assert "AUTONOMOUS_LIVE_CAPTURE_ENABLED" in alaveteli

    for name in ("au_nsw_historical_seed.yml", "au_jurisdiction_rollout.yml"):
        workflow = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert "confirm_live:" not in workflow
        assert "AUTONOMOUS_AU_CAPTURE_ENABLED" in workflow
        assert "environment: au-live-capture" in workflow


def test_nz_historical_replay_pilot_is_bounded_and_non_publishing() -> None:
    workflow = (WORKFLOWS / "nz_historical_replay_pilot.yml").read_text(encoding="utf-8")

    assert "source_run_id:" in workflow
    assert 'test "$REPLAY_LIMIT" -le 25' in workflow
    assert 'test "$DELAY_SECONDS" -ge 1' in workflow
    assert "actions/download-artifact" in workflow
    assert "enrich_historical_core.py" in workflow
    assert '"origin_contacted": False' in workflow
    assert '"publication": "none"' in workflow


def test_nz_historical_replay_batch_is_resumable_and_bounded() -> None:
    workflow = (WORKFLOWS / "nz_historical_replay_batch.yml").read_text(encoding="utf-8")

    assert "start_offset:" in workflow
    assert 'test "$REPLAY_LIMIT" -le 10' in workflow
    assert 'test "$RETRIES" -le 1' in workflow
    assert '--start-offset "$START_OFFSET"' in workflow
    assert '--retries "$RETRIES"' in workflow
    assert '"failed_record_count"' in workflow
    assert '"origin_contacted": False' in workflow
    assert '"publication": "none"' in workflow


def test_nz_source_index_uses_resumable_complete_cdx_export() -> None:
    workflow = (WORKFLOWS / "nz_historical_source_indexes.yml").read_text(encoding="utf-8")

    assert "cdx_limit:" not in workflow
    assert "page_size:" in workflow
    assert "max_pages:" in workflow
    assert "resume_run_id:" in workflow
    assert "actions: read" in workflow
    assert "fetch_complete_internet_archive_cdx.py" in workflow
    assert "--capture-mode url_index" in workflow
    assert "Fail closed on incomplete snapshot" in workflow
    assert "if: always()" in workflow
    assert "path: .tmp\n          github-token:" in workflow
    assert "--attachments-output dist/process-events/attachments.jsonl" in (
        WORKFLOWS / "historical_backfill_batch.yml"
    ).read_text(encoding="utf-8")


def test_nz_real_backfill_refuses_unreconciled_queues_and_leases_next_offset() -> None:
    workflow = (WORKFLOWS / "nz_real_backfill_batch.yml").read_text(encoding="utf-8")

    assert (
        "--captured-manifest .tmp/source/nz-historical-source-inputs/latest_manifest.json"
        in workflow
    )
    assert "reconciled queue does not match live captured manifest" in workflow
    assert "manifest_live_count" in workflow
    assert "jq -sr 'map(select(.source_url != null) | .source_url) | first // empty'" in workflow
    assert "| head -n 1" not in workflow
    assert "nz_backfill_controller.py next" in workflow
    assert "nz_backfill_controller.py abandon" in workflow
    assert "steps.failure_artifact.outputs.artifact-id != ''" in workflow
    assert 'workflow_conclusion: "failure"' in workflow
    assert "next_offset=$((START_OFFSET + BATCH_SIZE))" not in workflow
    assert "NEXT_OFFSET" not in workflow


def test_nz_real_backfill_monitor_dispatches_from_durable_state() -> None:
    workflow = (WORKFLOWS / "nz_real_backfill_monitor.yml").read_text(encoding="utf-8")

    assert "nz_backfill_controller.py next" in workflow
    assert "status in queued in_progress" in workflow
    assert '-f start_offset="${{ steps.state.outputs.next_offset }}"' in workflow
    assert "-f auto_batches_remaining=4" in workflow
    assert "-f state_label=nz-real-backfill-state" in workflow
    assert "-f max_auto_batches=" not in workflow
    assert "-f start_offset=0" not in workflow
