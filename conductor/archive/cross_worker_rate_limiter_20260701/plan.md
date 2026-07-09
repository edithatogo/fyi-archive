# Plan: cross_worker_rate_limiter_20260701

## Phase 1: Define the dependency contract

- [x] 1.1 Record the upstream implementation target in `fyi-cli` issue #2.
- [x] 1.2 Document the expected shared limiter semantics in this repo's conductor
      track so archive work can depend on it explicitly.
- [x] 1.3 Verify the current archive workflows still have safe per-process fallback
      pacing while the shared limiter is being built.

## Phase 2: Add verification hooks

- [x] 2.1 Extend archive verification/reporting expectations to surface limiter
      provenance or lease freshness when the shared limiter becomes available.
- [x] 2.2 Add a regression check for missing shared limiter metadata so the archive
      side fails loudly instead of silently over-pacing.
- [x] 2.3 Confirm the workflow and report paths still complete when the shared
      limiter is absent, using the existing per-process pacing fallback.

## Phase 3: Close the dependency loop

- [x] 3.1 Re-check the sibling `fyi-cli` implementation once the issue lands and
      align any archive-side consumer assumptions.
- [x] 3.2 Update the conductor registry with the final dependency state.
- [x] 3.3 Confirm the archive-side verification report reflects the shared limiter
      source and any observed backoff behavior.
