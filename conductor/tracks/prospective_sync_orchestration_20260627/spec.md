# Track: Prospective sync orchestration
Track ID: `prospective_sync_orchestration_20260627`

## Goal

A **daily, content-addressed** prospective sync: restore the corpus state from
Hugging Face, drive `fyi-cli`'s archival-content-diff to discover changes since the
last run, capture only added/updated requests, regenerate manifest + changes, upload
to HF, and **SHA-256-verify** the remote manifest against local.

## Prerequisites

- `fyi-cli` track `archival-content-diff` (added/updated/removed by content SHA-256).
- This repo's `historical_seed_orchestration` (provides the initial corpus + manifest).

## Scope

- `hf_sync.yml`: daily cron (`"17 14 * * *"`, family convention) + manual trigger.
  Concurrency group `hf-sync-${{ github.ref }}`, `cancel-in-progress: false`.
- Pipeline: HF `snapshot_download` restore → `fyi-cli` diff `--since last` →
  `fyi-cli` capture (new/changed only) → assemble manifest + changes →
  `upload_large_folder` → re-download remote manifest → SHA-256 compare → fail on
  mismatch.
- `data/_state/sync_state.json` holds the high-water mark (last successful sync).
- `latest_changes.json` (validated against `schemas/changes.schema.json`) committed as
  a job artifact and surfaced in the step summary.

## Out of scope

- Capture/diff implementation (that's `fyi-cli`).
- Multi-mirror publish beyond HF (see `multi_mirror_publish`).

## Acceptance criteria

- [ ] Daily cron runs green on an empty-diff day (idempotent, no churn).
- [ ] A deliberately-added test request is captured and appears in `latest_changes.json`.
- [x] Remote manifest SHA-256 mismatch fails the job.
- [x] `sync_state.json` advances its high-water mark only on a successful, verified
      run.
- [x] Concurrency: a second run while one is in flight does not cancel the first.

Live cron/capture proof remains blocked until the historical seed corpus is available;
`fyi-cli archival-content-diff` is now implemented, and dry-run unit coverage validates
empty-diff and new-record propagation locally.

## Risks

- HF rate limits / upload stalls → use `upload_large_folder` (resumable); surface
  stall errors into the step summary.
- Site-side schema drift (Alaveteli upgrade) → diff fails loudly; tracked as a learning
  candidate rather than silently skipped.
