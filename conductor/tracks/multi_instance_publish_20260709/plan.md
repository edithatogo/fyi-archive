# Plan: multi_instance_publish_20260709

## Phase 1: Foundations

- [x] per-instance HF repo config resolved from the instance registry, with explicit override support
- [x] draft-first AU publish workflow scope and instance guard
- [x] mirror verification evidence path retained by the publication workflow
- [x] dataset card AU exists and remains isolated from NZ publication paths

## Phase 2: Verification

- [x] Unit/integration tests or dry-run evidence
- [ ] Update track metadata status when complete
- [ ] Close GitHub sub-issues with evidence links

## Notes

- Capture remains in fyi-cli only (R-05, R-06, R-41).
- Public-policy research purpose, not AI training (R-43).
- Honour gentle archive defaults (two seconds between requests, one worker) plus fyi-cli safeguards (R-42).
