# Plan: prospective_sync_orchestration_20260627

## Phase 1: Sync command

- [~] 1.1 `fyi-archive sync --since last` subcommand: restore HF state, invoke
      `fyi-cli` diff + selective capture, assemble manifest + changes.
- [x] 1.2 `sync_state.json` high-water management; only advance on verified success.
- [x] 1.3 Unit tests: empty-diff idempotency; new-record propagation; rollback on
      verify failure.

## Phase 2: HF publish + verify

- [x] 2.1 `hf_publish.py` adapter using `upload_large_folder` + hf-xet.
- [x] 2.2 Remote manifest re-download + SHA-256 compare; fail job on mismatch.
- [x] 2.3 `latest_changes.json` validation against `schemas/changes.schema.json`.

## Phase 3: Workflow + health

- [x] 3.1 `hf_sync.yml` (daily cron, concurrency group, no cancel).
- [x] 3.2 Step-summary health line (counts, verify result) committed to
      `conductor/archive_health.json`.
- [x] 3.3 `actionlint` + `zizmor` clean.

## Dependencies / blocking

- `fyi-cli` track `archival-content-diff` is implemented; live empty-day proof still
  requires a seeded corpus and credentials.
- BLOCKED for seeded-corpus proof on this repo's
  `historical_seed_orchestration`.
