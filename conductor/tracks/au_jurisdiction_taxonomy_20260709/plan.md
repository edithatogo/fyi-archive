# Plan: au_jurisdiction_taxonomy_20260709

## Phase 1: Foundations

- [x] jurisdiction rules JSON
- [x] fixtures from RTK tags
- [x] mapping helpers + tests
- [x] authorities_au schema

## Phase 2: Verification

- [x] Unit/integration tests or dry-run evidence
- [ ] Update track metadata status when complete
- [x] Close GitHub sub-issues with evidence links

## Blocker

Live body-tag enumeration remains blocked on fyi-cli issue #84. The archive-side
taxonomy is deterministic and tested, but no live AU classification claim is made
until the companion capability is available.

## Notes

- Capture remains in fyi-cli only (R-05, R-06, R-41).
- Public-policy research purpose, not AI training (R-43).
- Honour default fyi-cli rate limits (~1 rps + jitter) unless justified (R-42).
