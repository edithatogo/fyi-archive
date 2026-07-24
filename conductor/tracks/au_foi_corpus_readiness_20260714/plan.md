# Plan: Australian FOI corpus readiness

## Phase 1: Sampling and rights contracts

- [ ] Task: Define jurisdiction, outcome, time, agency, correspondence, and
      attachment strata with explicit unknown categories.
- [ ] Task: Define source-rights, takedown, sensitive-data, and publication gates.
- [x] Task: Add manifest validation and cross-jurisdiction contamination tests.
- [ ] Task: Pin the initial Commonwealth and NSW sampling frame.

## Phase 2: Capped pilot capture

- [ ] Task: `[HUMAN]` Approve the bounded Commonwealth and NSW live-capture window.
- [ ] Task: Run `fyi-cli` capture through the existing shared limiter and AU paths.
- [ ] Task: Verify correspondence, attachment, WARC/WACZ, provenance, and digest completeness.
- [ ] Task: Report coverage gaps without expanding capture automatically.

## Phase 3: Validation releases

- [ ] Task: Freeze pilot manifests and publish draft-first validation snapshots.
- [ ] Task: Independently verify remote hashes and jurisdiction isolation.
- [ ] Task: Hand pinned samples to FOI-O and `nlp-policy-nz` tracks.
- [ ] Task: Record baseline and re-extraction dataset revisions separately.

## Phase 4: Remaining jurisdictions

- [ ] Task: Repeat the approved sampling and rights process for the other seven jurisdictions.
- [ ] Task: Verify every profile has representative evidence or an explicit insufficiency report.
- [ ] Task: Run repository quality gates and Conductor review.
- [ ] Task: Archive only after publication evidence and human gates are recorded.
