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

## Phase 3: Full backfill and continuation

- [x] Task: Add resumable full-corpus orchestration using existing historical backfill state.
- [x] Task: Add deterministic incremental merge, compaction, correction, and tombstone handling.
- [x] Task: Reconcile request/event/attachment coverage to pinned source revisions.
- [x] Task: Benchmark representative and complete archive runs.
- [x] Task: Phase verification and checkpoint per `conductor/workflow.md`.

## Phase 4: Dataset integration and downstream acceptance

- [x] Task: Add Dataset Viewer configs, metadata, provenance, and local publication dry-run.
- [ ] Task: Verify remote rows and shards only after the separate publication gate is authorized.

The local live benchmark runner is `scripts/benchmark_process_projection.py`.
It requires an explicitly supplied manifest, revision, and event input, verifies
the generated checksums, and performs no publication.
- [x] Task: Supply pinned fixtures and digests to `foi-process` T10.
- [x] Task: Record acceptance evidence in GitHub issue #196 and parent epic #36.
- [x] Task: Phase verification and checkpoint per `conductor/workflow.md`.
- [x] Local contract tests and checksum verification pass; 204 tests pass, 1 skipped.
