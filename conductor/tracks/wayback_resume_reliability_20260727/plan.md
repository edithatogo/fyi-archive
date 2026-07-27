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
- [ ] Record the follow-up hosted continuation evidence.
- [ ] Complete the track only after hosted evidence passes.
