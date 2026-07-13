# Improvement Backlog

Candidate improvements surfaced during work or from CI-learning-candidates. Promote
items into a concrete track when ready to act.

## Candidates

- [ ] Review and enable optional Sigstore/cosign keyless signing for release artifacts
      after `publish_archives.yml` and the Zenodo production gate are stable. See
      `docs/sigstore-signing.md`.
      **Status (2026-07-13):** intentionally not promoted. Release `0.11.1`
      attaches SBOM/provenance evidence and production Zenodo DOI publication
      is now verified, but release payload signing has not yet been exercised.

## Operational (active)

Snapshot: [`operations_status.json`](./operations_status.json). Historical notes
below are retained for audit context and are not the current controller state.

- [x] Full-site historical backfill dispatch and merge drain — controller state
      now reports `complete: true`, `next_id: 250001`, and `pending_batches: 0`.
      Procedure and historical incidents remain documented in:
      [`docs/backfill-ops-runbook.md`](../docs/backfill-ops-runbook.md).
- [x] Maintain mirror publication parity for the current draft-first scope.
      HF, Zenodo draft, and OSF all have verified non-zero evidence; OSF retry
      consistency is bounded and recorded in `operations_status.json`.
- [x] `conductor/archive_health.json` is **gitignored** — treat GHA artifacts +
      doctor output as source of truth; do not commit local zeros as status.
- [x] Controller re-queues pending batches when dispatch is complete and no
      worker slots are active, with bounded serial retries.
- [x] Health-monitor summaries expose measurable coverage progress without
      additional source requests (`target_records`, `remaining_to_target`, and
      `target_met`).
