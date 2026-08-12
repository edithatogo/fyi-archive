from pathlib import Path

CONTROLLER = Path(".github/workflows/alaveteli_working_sites.yml").read_text(encoding="utf-8")
WORKER = Path(".github/workflows/alaveteli_instance_capture.yml").read_text(encoding="utf-8")


def test_instances_run_in_parallel_but_each_instance_is_serialized() -> None:
    assert "fail-fast: false" in CONTROLLER
    assert "max-parallel: 4" in CONTROLLER
    assert "uses: ./.github/workflows/alaveteli_instance_capture.yml" in CONTROLLER
    assert "group: alaveteli-working-site-${{ inputs.instance }}" in WORKER
    assert "cancel-in-progress: false" in WORKER
    assert "group: alaveteli-working-sites\n" not in CONTROLLER + WORKER


def test_reusable_worker_has_a_bounded_per_instance_interface() -> None:
    assert "workflow_call:" in WORKER
    assert "instance: ${{ matrix.instance }}" in CONTROLLER
    assert "enabled: ${{ github.event_name == 'schedule'" in CONTROLLER
    assert "if: ${{ inputs.enabled }}" in WORKER
    assert "instance: [se-handlingar, ua-dostup, uy-quesabes, ge-askgov]" in CONTROLLER


def test_source_urls_cannot_be_overridden_and_are_resolved_from_configuration() -> None:
    workflows = CONTROLLER + WORKER
    assert "catalog_url:" not in CONTROLLER
    assert "capture_base_url:" not in CONTROLLER
    assert "CATALOG_URL_OVERRIDE" not in workflows
    assert "CAPTURE_BASE_URL_OVERRIDE" not in workflows
    assert 'get_instance("\'"$INSTANCE"\'").catalog_url' in WORKER
    assert 'get_instance("\'"$INSTANCE"\'").capture_base_url()' in WORKER


def test_source_network_operations_remain_delegated_to_pinned_fyi_cli() -> None:
    for direct_client in (
        "curl ",
        "wget ",
        "Invoke-WebRequest",
        "urllib.request",
        "requests.get(",
        "httpx.",
    ):
        assert direct_client not in WORKER
    assert "uv run fyi discover" in WORKER
    assert "uv run fyi-archive discover bodies" in WORKER
    assert "uv run fyi-archive seed run" in WORKER
    for line in WORKER.splitlines():
        stripped = line.strip()
        if stripped.startswith("- uses:"):
            action = stripped.removeprefix("- uses: ")
            assert "@" in action
            assert len(action.rsplit("@", 1)[1].split()[0]) == 40


def test_request_discovery_uses_checkpointed_feed_before_bounded_fallback() -> None:
    discovery = WORKER[WORKER.index("Discover next request queue page") :]
    assert "Prepare resumable request queue" in WORKER
    assert "steps.queue.outputs.pending == '0'" in discovery
    assert "--checkpoint" in discovery
    assert '--max-pages "$DISCOVERY_MAX_PAGES"' in discovery
    assert "--backfill-ids" in discovery
    assert "manage_alaveteli_queue.py" in discovery


def test_live_manifest_reads_fyi_cli_raw_request_tree() -> None:
    manifest = WORKER[WORKER.index("Build manifest") :]
    assert 'if [ "$DRY_RUN" != "true" ]; then' in manifest
    assert 'derived="$root/raw/requests"' in manifest


def test_explicit_live_capture_fails_when_ledger_or_manifest_is_empty() -> None:
    verification = WORKER[WORKER.index("Verify explicit live capture") :]
    assert 'entry.get("status") != "completed"' in verification
    assert "record_count < 1" in verification
    assert "inputs.request_ref != ''" in verification
    assert "!inputs.dry_run" in verification


def test_workflow_restores_only_verified_live_state() -> None:
    restore = WORKER[WORKER.index("Restore latest verified site state") :]
    assert "gh run list" in restore
    assert "gh run download" in restore
    assert '"status": "completed"' in restore
    assert '"dry_run": false' in restore
    assert "find \"$candidate\" -type f -path '*/_state/ledger.jsonl'" in restore
    assert 'cp -a "$site_root/." "$root/"' in restore
