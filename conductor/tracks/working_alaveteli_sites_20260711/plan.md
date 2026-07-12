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
      [Sweden run 29192823057](https://github.com/edithatogo/fyi-archive/actions/runs/29192823057)
      failed closed with HTTP 403 and no capture;
      [Ukraine run 29192878464](https://github.com/edithatogo/fyi-archive/actions/runs/29192878464)
      captured one request and produced one manifest record;
      [Georgia run 29192826001](https://github.com/edithatogo/fyi-archive/actions/runs/29192826001)
      captured one request and produced one manifest record; and
      [Uruguay run 29192484464](https://github.com/edithatogo/fyi-archive/actions/runs/29192484464)
      captured one request and produced one manifest record with two WARC
      record IDs.
