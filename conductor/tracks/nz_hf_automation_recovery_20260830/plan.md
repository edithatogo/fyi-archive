# Implementation plan

- [x] Establish regression cases for exact failed owners, live/successful owners, stale observations, replacement and range conflicts.
- [x] Implement pure recovery transition and stop monitor redispatch while a lease exists.
- [x] Add serialized prepare/retain/recheck/apply workflow with default diagnosis-only mode and main-branch application guard.
- [x] Reproduce contaminated stdout, stale summary, path collision and cross-instance card failures.
- [x] Implement dedicated atomic summary, stderr diagnostics, strict card inputs and always-retained bounded execution receipt.
- [~] Run complete tests, repository quality and workflow validation; record host-tool limitations separately.
- [ ] Verify exact hosted CI, retained recovery artifact and real controlled lease recovery; observe subsequent progress without skipping work.
- [ ] Verify public manifest/card consistency and close only the completed repair scope.

## Review fixes

- [x] Make recovery receipt and workflow-file encoding explicit for cross-platform CI. Commit `a0a4d45`; preview lint, ty and six recovery integration tests passed.

## Raw-retention incident follow-up

- [x] Inspect the actual bounded hosted artifact and distinguish credited capture from retained original bytes; preserve historical credit evidence.
- [x] Pause NZ automatic dispatch after confirming raw directories were omitted.
- [x] Add failing missing/corrupt/WARC/path/restore tests and require original-byte inventory plus clean artifact restore before queue credit; validate locally.
- [~] Verify hosted raw-retention repair and a bounded retained capture. Automatic dispatch remains disabled.
- [ ] Reconcile historic raw gaps and durable storage before enabling sustained backfill; do not classify temporary artifacts as public HF preservation.

- [~] Follow-up: attachment discovery census, no credit for gaps, and safe CI failure reporting. Local validation passed; hosted checks and merge pending. Receipt: attachment-gap-validation.json.
