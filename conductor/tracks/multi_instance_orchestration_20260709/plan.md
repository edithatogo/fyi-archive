# Plan: multi_instance_orchestration_20260709

## Phase 1: Foundations

- [x] instances registry module
- [x] CLI --instance and FYI_ARCHIVE_BASE_URL
- [x] manifest schema multi-source
- [x] seed/sync pass --base-url to fyi-cli
- [x] NZ regression tests

## Phase 2: Verification

- [x] Unit/integration tests or dry-run evidence
- [x] Update track metadata status when complete
- [x] Close GitHub sub-issues with evidence links

## Notes

- Capture remains in fyi-cli only (R-05, R-06, R-41).
- Public-policy research purpose, not AI training (R-43).
- Honour default fyi-cli rate limits (~1 rps + jitter) unless justified (R-42).
