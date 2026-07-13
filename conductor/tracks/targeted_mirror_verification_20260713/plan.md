# Implementation plan

- [x] Add a regression test that reproduces stale-other-mirror evidence during
      a targeted retry.
- [x] Write versioned evidence from the current verification targets while
      preserving the aggregate report.
- [x] Add bounded post-upload OSF listing retries for eventual consistency.
- [x] Run focused and full test/quality checks.
- [x] Merge the protected-branch PR; live OSF-only verification retry launched
      after merge and remains operational evidence to refresh.
