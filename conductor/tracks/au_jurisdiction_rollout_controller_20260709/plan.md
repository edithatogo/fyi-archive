# Plan: au_jurisdiction_rollout_controller_20260709

## Phase 1: Foundations

- [x] jurisdiction order config
- [x] GHA controller + issue state
- [x] merge national manifest
- [x] shared rate-limit name

## Phase 2: Verification

- [x] Unit/integration tests or dry-run evidence (workflow run [29096913489](https://github.com/edithatogo/fyi-archive/actions/runs/29096913489), 10 records merged)
- [~] Update track metadata status after the first verified non-dry-run rollout
- [ ] Close GitHub sub-issues with evidence links after live evidence is attached

## Implementation status

- [x] fyi-cli catalog override and provenance support landed in v1.2.0 (PR #158).
- [x] Verified GitHub artifact fallback and provenance sidecar landed in fyi-archive.
- [x] Capped sequential live worker now performs discovery, capture, per-jurisdiction
      manifests, and national merge.
- [ ] Run the first non-dry-run rollout with an approved catalog source or a retained
      successful catalog artifact; do not claim production completion before its evidence.

## Notes

- Capture remains in fyi-cli only (R-05, R-06, R-41).
- Public-policy research purpose, not AI training (R-43).
- Honour the archive gentle defaults (two seconds between requests, one capture worker)
  and fyi-cli robots/User-Agent/shared-limiter safeguards unless an operator explicitly
  approves a slower or otherwise source-compatible setting (R-42).
