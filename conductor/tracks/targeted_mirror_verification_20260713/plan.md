# Implementation plan

- [x] Add a regression test that reproduces stale-other-mirror evidence during
      a targeted retry.
- [x] Write versioned evidence from the current verification targets while
      preserving the aggregate report.
- [x] Add bounded post-upload OSF listing retries for eventual consistency.
- [x] Run focused and full test/quality checks.
- [ ] Merge the protected-branch PR and run a live OSF-only verification retry.
