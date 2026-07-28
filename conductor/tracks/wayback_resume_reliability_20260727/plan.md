# Plan: Wayback resume reliability

- [x] Record run `30241894770` outcomes and checkpoint evidence.
- [x] Define fail-closed retry and resume requirements.
- [x] Add CDX retry regression tests.
- [x] Add automatic workflow-resume contract tests.
- [x] Implement bounded page-level transient retries.
- [x] Implement verified automatic checkpoint restoration.
- [x] Preserve explicit resume precedence and provenance.
- [x] Run focused tests and lint.
- [x] Run the repository quality suite: 368 passed and 1 skipped; the existing
  repository formatter baseline remains red on unrelated files.
- [x] Record hosted continuation run `30250397882`: 29 independent artifacts,
  12 advancing targets, 34,674 additional records, and 23 fail-closed targets.
- [x] Add malformed-response retries with patient bounded backoff.
- [x] Reduce hosted CDX concurrency and extend the per-pattern deadline.
- [x] Fresh-start refreshes after the newest compatible complete inventory.
- [x] Re-run focused and repository quality gates for the follow-up.
- [x] Record run `30252925334`: all 29 artifacts retained, 88,004 additional
  records across 11 sites, NZ at 53,564 records, and 24 fail-closed targets.
- [x] Add a bounded sequential resume-key paginator with regression tests.
- [x] Persist hash-verified cursor checkpoints and explicit pagination provenance.
- [x] Reject incompatible legacy page checkpoints in cursor workflows.
- [x] Run the repository and hosted quality gates for cursor pagination.
- [x] Record cursor-based hosted continuation `30262962651`: all 29 artifacts
  retained; 16 complete inventories and 13 fail-closed failures.
- [x] Add a bounded manual `site_id` selector for targeted retries; scheduled
  runs continue to enumerate the full site matrix.
- [ ] Complete the track only after hosted evidence passes.

## Weekly reconciliation 30339737294 and bounded targeted follow-up

- [x] Reconcile the weekly run `30339737294`: 29 artifacts retained, 22
  complete and 7 fail-closed; aggregate retained records `500,573`.
- [x] Record the seven incomplete sites and the explicit NZ observation:
  `au-rtk` 40,000, `ca-federal-atip` 54,000, `de-fragdenstaat` 67,000,
  `eu-asktheeu` 56,000, `nz-fyi` 50,000, `ua-dostup` 42,000, and `uk-wdtk`
  26,000. NZ remains incomplete; no national denominator is available.
- [x] Execute bounded targeted follow-up: AU run `30365391104` completed with
  63,473 records; UA run `30365404274` remained fail-closed at 50,000 after
  HTTP 503. UK retry `30369505285` was cancelled after a stale snapshot.
- [x] Verify named-site selector behavior through terminal runs. Attempts
  using invalid ids (`30370087242`, `30370285224`, `30370349930`,
  `30370464238`) failed closed during enumeration; the valid CA attempt
  `30370646140` exceeded the bounded observation window without a terminal
  update and was not retried indefinitely.
- [ ] Acceptance remains open: CA, DE, EU, NZ, UK, and UA are not all complete.
  They resume on the existing weekly schedule; targeted dispatches remain an
  optional operator-controlled improvement, not an unbounded retry loop.

## Targeted-run reliability follow-up

- [x] Diagnose queued targeted-run cancellations as a consequence of separate
  dispatches sharing the deliberate global CDX concurrency group.
- [x] Add a comma-separated multi-site selector that produces one bounded matrix
  while preserving `max-parallel: 2` and the existing single-site input.
- [x] Add explicit valid-id diagnostics and reject mixed, empty, duplicate, or
  unknown targeted selections before acquisition.
- [x] Emit minute-level workflow heartbeats plus checkpoint progress without
  logging raw resume keys.
- [x] Extend transient request attempts with a 60-second backoff ceiling so the
  patient retry loop can use the existing whole-pattern deadline.
- [x] Run focused and repository quality gates for the follow-up: 394 passed,
  1 skipped; Ruff, ty, Actionlint, and Zizmor passed.
- [ ] Record a bounded hosted multi-site continuation and inspect every retained
  site artifact before closing acceptance.
