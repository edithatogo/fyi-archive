# Plan: working_alaveteli_sites_20260711

- [x] Verify candidate deployments and catalog endpoints with low-rate probes.
- [x] Add instance registry metadata and separate catalog URLs.
- [x] Add sequential overnight workflow with explicit live confirmation.
- [x] Add per-site artifact retention and operator documentation.
- [x] Run the workflow dry run and inspect all four artifacts (GitHub run
      [29154363956](https://github.com/edithatogo/fyi-archive/actions/runs/29154363956);
      four manifests, two deterministic records each).
- [x] Run one explicitly confirmed capped live smoke per site, if permitted by
      the deployment's robots and response behavior. Evidence:
      [Sweden run 29193015589](https://github.com/edithatogo/fyi-archive/actions/runs/29193015589)
      failed closed with an explicit ledger `status=failed` and HTTP 403;
      [Ukraine run 29192878464](https://github.com/edithatogo/fyi-archive/actions/runs/29192878464)
      captured one request and produced one manifest record;
      [Georgia run 29192971469](https://github.com/edithatogo/fyi-archive/actions/runs/29192971469)
      captured one request and produced one manifest record; and
      [Uruguay run 29192938680](https://github.com/edithatogo/fyi-archive/actions/runs/29192938680)
      captured one request and produced one manifest record. The explicit-smoke
      verifier now fails the job when the ledger is not completed or the
      manifest is empty.

## Residual source limitation

`handlingar.se` exposes a readable authority catalog, but the selected public
request endpoint returned `403 Forbidden` during the capped smoke. The artifact
is retained as evidence; no successful Swedish request capture is claimed.
