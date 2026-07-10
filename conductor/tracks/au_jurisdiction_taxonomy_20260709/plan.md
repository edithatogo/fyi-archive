# Plan: au_jurisdiction_taxonomy_20260709

## Phase 1: Foundations

- [x] jurisdiction rules JSON
- [x] fixtures from RTK tags
- [x] mapping helpers + tests
- [x] authorities_au schema

## Phase 2: Verification

- [x] Unit/integration tests or dry-run evidence
- [x] Delegate live body enumeration to merged fyi-cli `discover-bodies`
- [x] Update track metadata status when complete
- [x] Close GitHub sub-issues with evidence links

## Resolved blocker

The companion capability landed in fyi-cli PR #137. The AU historical-seed
workflow now invokes `fyi-archive discover bodies`, which delegates to
`fyi-cli discover-bodies` using its robots-aware pacing and shared limiter DB.
The live AU smoke returned 2,722 bodies. This proves the enumeration path only;
the remaining NSW capture and full AU rollout are tracked separately.

## Notes

- Capture remains in fyi-cli only (R-05, R-06, R-41).
- Public-policy research purpose, not AI training (R-43).
- Honour default fyi-cli rate limits (~1 rps + jitter) unless justified (R-42).
