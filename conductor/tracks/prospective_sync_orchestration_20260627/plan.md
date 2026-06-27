# Plan: prospective_sync_orchestration_20260627

## Phase 1: Sync command

- [ ] 1.1 `fyi-archive sync --since last` subcommand: restore HF state, invoke
      `fyi-cli` diff + selective capture, assemble manifest + changes.
- [ ] 1.2 `sync_state.json` high-water management; only advance on verified success.
- [ ] 1.3 Unit tests: empty-diff idempotency; new-record propagation; rollback on
      verify failure.

## Phase 2: HF publish + verify

- [ ] 2.1 `hf_publish.py` adapter using `upload_large_folder` + hf-xet.
- [ ] 2.2 Remote manifest re-download + SHA-256 compare; fail job on mismatch.
- [ ] 2.3 `latest_changes.json` validation against `schemas/changes.schema.json`.

## Phase 3: Workflow + health

- [ ] 3.1 `hf_sync.yml` (daily cron, concurrency group, no cancel).
- [ ] 3.2 Step-summary health line (counts, verify result) committed to
      `conductor/archive_health.json`.
- [ ] 3.3 `actionlint` + `zizmor` clean.

## Dependencies / blocking

- BLOCKED on `fyi-cli` track `archival-content-diff`.
- BLOCKED on this repo's `historical_seed_orchestration`.
