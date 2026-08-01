# Plan: Full-corpus process projection and continuation

## Phase 1: Contract and derived-layer boundary

- [x] Task: Pin and validate the `fyi-cli` process-event contract and fixtures.
- [x] Task: Define schemas, partition keys, rights metadata, and projection identity.
- [x] Task: Add negative tests preventing raw/derived conflation and excluded-field leakage.
- [x] Task: Phase verification and checkpoint per `conductor/workflow.md`.

## Phase 2: Projection generation

- [x] Task: Write failing tests for case, event, attachment, revision, and coverage tables.
- [x] Task: Implement deterministic bounded Parquet generation and checksums.
- [x] Task: Preserve source order, revision sequence, and stable identifiers across shards.
- [x] Task: Add recursive privacy and takedown propagation tests. Stable-ID
      takedown propagation and public-output linked-object suppression are
      implemented and tested.
- [x] Task: Phase verification and checkpoint per `conductor/workflow.md`.

## Phase 3: Verified full backfill and continuation

- [ ] Task: Replace the public dry-run placeholder manifest with a reliable authoritative or explicitly reconciled archive snapshot.
- [ ] Task: Regenerate fyi-cli event and attachment sidecars for every captured request, with resumable continuation.
- [x] Task: Preserve deterministic incremental merge, compaction, correction, and tombstone handling.
- [ ] Task: Require exact request/case/event/attachment parity to a pinned live source revision, with reviewed exclusions only.
- [x] Task: Reject dry-run manifests from full-corpus process projections and publication artifacts.
- [ ] Task: Benchmark a representative live slice and the reconciled complete archive run.
- [ ] Task: Phase verification and checkpoint per `conductor/workflow.md`.

## Phase 4: Dataset integration and downstream acceptance

- [x] Task: Add Dataset Viewer configs, metadata, provenance, and local publication dry-run.
- [ ] Task: Publish a versioned takedown inventory digest and carry its revision into downstream acceptance evidence.
- [ ] Task: Verify remote rows and shards only after the separate publication gate is authorized and full-corpus parity passes.

The local live benchmark runner is `scripts/benchmark_process_projection.py`.
It requires an explicitly supplied manifest, revision, and event input, verifies
the generated checksums, and performs no publication.
- [x] Task: Supply pinned fixtures and digests to `foi-process` T10.
- [x] Task: Record acceptance evidence in GitHub issue #196 and parent epic #36.
- [x] Task: Phase verification and checkpoint per `conductor/workflow.md`.
- [x] Local contract tests and checksum verification pass; this does not satisfy the reopened live full-corpus parity gate.

## 2026-08-01 hosted corpus recovery

- The canonical Hugging Face manifest and Parquet projection were restored to
  the last verified 33,217-record revision after a one-record sample publish.
- This repairs hosted mirror parity and the Dataset Viewer, but does **not**
  close Phase 3: full WARC/event/attachment parity, reviewed exclusions, a
  takedown digest, and a pinned complete-source revision remain outstanding.
