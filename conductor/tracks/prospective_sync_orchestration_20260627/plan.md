# Plan: prospective_sync_orchestration_20260627

## Phase 1: Sync command

- [x] 1.1 `fyi-archive sync --since last` subcommand: restore HF state, invoke
      `fyi-cli` diff + selective capture, assemble manifest + changes
      (GHA run 28378940339 at d575583 proved restore + real `fyi diff` +
      empty-change verification against HF).
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

- UNBLOCKED: seeded-corpus empty-diff proof passed on GHA run 28378940339 with
  `added: []`, `updated: []`, `removed: []`, record_count 1, and remote HF
  manifest verification true. A preceding normalization run 28378701221 proved
  non-empty sync changes publish before verification.
