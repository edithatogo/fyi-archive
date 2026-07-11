# Plan: au_jurisdiction_rollout_controller_20260709

## Phase 1: Foundations

- [x] jurisdiction order config
- [x] GHA controller + issue state
- [x] merge national manifest
- [x] shared rate-limit name

## Phase 2: Verification

- [x] Unit/integration tests or dry-run evidence (workflow run [29096913489](https://github.com/edithatogo/fyi-archive/actions/runs/29096913489), 10 records merged)
- [x] Record implementation-complete status with dry-run evidence and an explicit live-operation gate
- [x] Close implementation parent issue with evidence links; retain live evidence as an operational gate

## Implementation status

- [x] fyi-cli catalog override and provenance support landed in v1.2.0 (PR #158).
- [x] Verified GitHub artifact fallback and provenance sidecar landed in fyi-archive.
- [x] Capped sequential live worker now performs discovery, capture, per-jurisdiction
      manifests, and national merge.
- [x] Document the first non-dry-run rollout as an operator-approved follow-up; do not
      claim production completion from dry-run evidence.

## Evidence

- Ordered controller dry-run [29144873699](https://github.com/edithatogo/fyi-archive/actions/runs/29144873699) produced a complete 10-record national manifest.
- Live execution is protected by explicit confirmation and the `au-live-capture` environment; no production completion is claimed here.

## Notes

- Capture remains in fyi-cli only (R-05, R-06, R-41).
- Public-policy research purpose, not AI training (R-43).
- Honour the archive gentle defaults (two seconds between requests, one capture worker)
  and fyi-cli robots/User-Agent/shared-limiter safeguards unless an operator explicitly
  approves a slower or otherwise source-compatible setting (R-42).
