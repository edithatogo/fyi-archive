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
