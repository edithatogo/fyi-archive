# Improvement Backlog

Candidate improvements surfaced during work or from CI-learning-candidates. Promote
items into a concrete track when ready to act.

## Candidates

- [ ] Review and enable optional Sigstore/cosign keyless signing for release artifacts
      after `publish_archives.yml` and the Zenodo production gate are stable. See
      `docs/sigstore-signing.md`.
      **Status (2026-07-09):** intentionally not promoted. Foundation tracks and
      draft-first mirror publish are delivered; keep this gated until production
      Zenodo + release attach paths run cleanly for a few cycles.

## Operational (active)

Snapshot: [`operations_status.json`](./operations_status.json) (2026-07-09).

- [~] Full-site historical backfill toward coverage target — **dispatch complete,
      merge drain required**. Issue #9: ~33 244 captured records, `next_id` 142 501,
      `dispatch_next_id` 250 001, ~195 pending merges. Procedure:
      [`docs/backfill-ops-runbook.md`](../docs/backfill-ops-runbook.md).
- [ ] Populate HF/OSF/Zenodo mirrors so health-monitor counts leave 0 (Phase B of
      ops runbook; latest monitor run 28989825250 still all zeros).
- [ ] `conductor/archive_health.json` is **gitignored** — treat GHA artifacts +
      doctor output as source of truth; do not commit local zeros as status.
- [ ] Optional hardening: controller should re-queue merges for `pending` batches
      when `planned_count == 0` but `pending_batches > 0` (today it no-ops).
