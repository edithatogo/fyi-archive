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

Snapshot: [`operations_status.json`](./operations_status.json). Historical notes
below are retained for audit context and are not the current controller state.

- [x] Full-site historical backfill dispatch and merge drain — controller state
      now reports `complete: true`, `next_id: 250001`, and `pending_batches: 0`.
      Procedure and historical incidents remain documented in:
      [`docs/backfill-ops-runbook.md`](../docs/backfill-ops-runbook.md).
- [~] Maintain mirror publication parity. HF and Zenodo have verified non-zero
      snapshots; OSF remains a separately retryable publication target after a
      documented 502 response.
- [ ] `conductor/archive_health.json` is **gitignored** — treat GHA artifacts +
      doctor output as source of truth; do not commit local zeros as status.
- [~] Controller re-queues pending batches when dispatch is complete and no worker
      slots are active. This is being implemented in the maintenance-hardening
      track with bounded serial retries.
