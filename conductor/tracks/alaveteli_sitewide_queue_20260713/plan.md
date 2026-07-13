# Plan: alaveteli_sitewide_queue_20260713

- [x] Inspect fyi-cli feed pagination and checkpoint behavior.
- [x] Add durable queue merge and verified-completion pruning.
- [x] Make workflow discovery feed-first with bounded fallback.
- [x] Restore prior verified site artifacts between runners.
- [x] Add focused queue and workflow tests.
- [ ] Run a live scheduled cycle on each accessible site and verify queue
      progress and retained artifacts.
- [ ] Reconcile queue-empty state and manifests for each site.
- [ ] Obtain an alternative permitted endpoint or operator export for Sweden.

## Current live evidence

- Uruguay: [run 29250015751](https://github.com/edithatogo/fyi-archive/actions/runs/29250015751), one completed record.
- Georgia: [run 29250090074](https://github.com/edithatogo/fyi-archive/actions/runs/29250090074), one completed record.
- Ukraine: [run 29250244671](https://github.com/edithatogo/fyi-archive/actions/runs/29250244671), one completed record.
- Sweden: [run 29193015589](https://github.com/edithatogo/fyi-archive/actions/runs/29193015589), failed closed with HTTP 403.
