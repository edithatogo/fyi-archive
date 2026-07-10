# Plan: au_nsw_historical_seed_20260709

## Phase 1: Foundations

- [x] NSW body queue
- [x] isolated data/au-rtk/nsw paths
- [x] workflow inputs instance+jurisdiction
- [x] capped smoke + evidence (workflow run [29095853547](https://github.com/edithatogo/fyi-archive/actions/runs/29095853547), 5 records, manifest scope guard passed)

## Phase 2: Verification

- [x] Unit/integration tests or dry-run evidence
- [x] Update track metadata status when complete
- [x] Close GitHub sub-issues with evidence links (workflow evidence is retained as the durable proof)

## Notes

- Capture remains in fyi-cli only (R-05, R-06, R-41).
- Public-policy research purpose, not AI training (R-43).
- Honour default fyi-cli rate limits (~1 rps + jitter) unless justified (R-42).
