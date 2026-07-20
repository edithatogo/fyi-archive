# Plan: Full-corpus process projection and continuation

## Phase 1: Contract and derived-layer boundary

- [ ] Task: Pin and validate the `fyi-cli` process-event contract and fixtures.
- [ ] Task: Define schemas, partition keys, rights metadata, and projection identity.
- [ ] Task: Add negative tests preventing raw/derived conflation and excluded-field leakage.
- [ ] Task: Phase verification and checkpoint per `conductor/workflow.md`.

## Phase 2: Projection generation

- [ ] Task: Write failing tests for case, event, attachment, revision, and coverage tables.
- [ ] Task: Implement deterministic bounded Parquet generation and checksums.
- [ ] Task: Preserve source order, revision sequence, and stable identifiers across shards.
- [ ] Task: Add recursive privacy and takedown propagation tests.
- [ ] Task: Phase verification and checkpoint per `conductor/workflow.md`.

## Phase 3: Full backfill and continuation

- [ ] Task: Add resumable full-corpus orchestration using existing historical backfill state.
- [ ] Task: Add deterministic incremental merge, compaction, correction, and tombstone handling.
- [ ] Task: Reconcile request/event/attachment coverage to pinned source revisions.
- [ ] Task: Benchmark representative and complete archive runs.
- [ ] Task: Phase verification and checkpoint per `conductor/workflow.md`.

## Phase 4: Dataset integration and downstream acceptance

- [ ] Task: Add Dataset Viewer configs, metadata, provenance, and local publication dry-run.
- [ ] Task: Verify remote rows and shards only after the separate publication gate is authorized.
- [ ] Task: Supply pinned fixtures and digests to `foi-process` T10.
- [ ] Task: Record acceptance evidence in GitHub issue #196 and parent epic #36.
- [ ] Task: Phase verification and checkpoint per `conductor/workflow.md`.
