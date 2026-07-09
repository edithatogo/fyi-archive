# Track: Cross-worker rate limiter
Track ID: `cross_worker_rate_limiter_20260701`

## Goal

Ensure the sibling `fyi-cli` repo provides a shared cross-worker limiter or shared
backoff mechanism so concurrent archive discovery and sync jobs bound aggregate
request rate, not just per-process pacing.

## Prerequisites

- `fyi-cli` issue `#2` is open and used as the implementation anchor.
- Existing per-process pacing in `fyi-cli` remains as a fallback.

## Scope

- Define the shared limiter contract in `fyi-cli`.
- Prefer a durable coordination mechanism over in-memory-only pacing.
- Add observability for limiter state or lease freshness so the archive side can
  verify it in CI and workflows.
- Expose enough metadata for this repo to report the limiter source in future
  verification output.

## Out of scope

- Rewriting FYI capture logic in this repo.
- Replacing per-process retries or backoff entirely.
- Changing the archive content model.

## Acceptance criteria

- [ ] A shared limiter/backoff mechanism exists in `fyi-cli` and is documented.
- [ ] Concurrent workers no longer each think they own the full request budget.
- [ ] 429 / transient failure handling feeds into the shared limiter state.
- [ ] The limiter can be observed or verified from job output or logs.
- [ ] Archive-side verification can describe whether shared limiter state was present.

## Recommendation

The limiter should be durable, low-overhead, and jittered. A small SQLite-backed
lease/token record is the cleanest fit for the existing tooling, and it should
report its current budget/lease state so backfill jobs can prove aggregate pacing
rather than merely assume it.
