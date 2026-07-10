# Plan: au_jurisdiction_rollout_controller_20260709

## Phase 1: Foundations

- [x] jurisdiction order config
- [x] GHA controller + issue state
- [x] merge national manifest
- [x] shared rate-limit name

## Phase 2: Verification

- [x] Unit/integration tests or dry-run evidence (workflow run [29096913489](https://github.com/edithatogo/fyi-archive/actions/runs/29096913489), 10 records merged)
- [ ] Update track metadata status when complete
- [ ] Close GitHub sub-issues with evidence links

## Remaining blocker

- [ ] Enable live jurisdiction workers after the GitHub-hosted runner can access the AU catalog or fyi-cli issue #155 is implemented.

## Notes

- Capture remains in fyi-cli only (R-05, R-06, R-41).
- Public-policy research purpose, not AI training (R-43).
- Honour default fyi-cli rate limits (~1 rps + jitter) unless justified (R-42).
