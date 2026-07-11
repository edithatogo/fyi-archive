# Plan: multi_instance_publish_20260709

## Phase 1: Foundations

- [x] per-instance HF repo config resolved from the instance registry, with explicit override support
- [x] draft-first AU publish workflow scope and instance guard
- [x] mirror verification evidence path retained by the publication workflow
- [x] dataset card AU exists and remains isolated from NZ publication paths

## Phase 2: Verification

- [x] Unit/integration tests or dry-run evidence
- [x] Update track metadata status when complete
- [x] Close GitHub sub-issues with evidence links

## Notes

- Capture remains in fyi-cli only (R-05, R-06, R-41).
- Public-policy research purpose, not AI training (R-43).
- Honour gentle archive defaults (two seconds between requests, one worker) plus fyi-cli safeguards (R-42).

## Evidence

- Network-independent AU publication dry-run [29146250634](https://github.com/edithatogo/fyi-archive/actions/runs/29146250634) produced an `au-rtk` manifest with 3 synthetic records, publication artifacts, and verification metadata recording `remote_reads=false` and `remote_writes=false`.
- Real mirror publication remains a separately gated operational action and is not claimed by this track.
