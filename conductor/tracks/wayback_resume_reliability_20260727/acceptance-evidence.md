# Acceptance evidence: Wayback resume reliability

## Hosted source evidence

- Initial run: `30241894770`.
- Automatic continuation: `30250397882`.
- Artifact boundary: 29 independently retained site artifacts per run.
- Continuation result: 12 targets advanced by 34,674 records and 37 pages.
- New Zealand advanced from 25,564 to 27,564 records and from 26 to 28 pages.
- Six zero-record inventories completed; 23 targets remained fail-closed.

The comparison was derived from each retained artifact's `manifest.json` and
retrieval evidence. Record and page deltas are observations from those files,
not estimates of total national FOI coverage.

## Transformation and provenance controls

- The CDX response remains a paginated cumulative URL inventory.
- URL-level mode retains the documented `urlkey` collapse; no inferred records
  are created.
- Checkpoint pages and configuration hashes remain validated by the fetch
  wrapper before resumption.
- A complete compatible manifest causes a fresh retrieval, preventing an older
  incomplete checkpoint from becoming the basis of a later refresh.
- The selected resume run and reason remain embedded in each site manifest.
- Origin FOI sites are not contacted and token permissions are unchanged.

## Local verification

- Focused tests: `19 passed`.
- Repository tests: `372 passed, 1 skipped`.

## Patient-retry hosted continuation

Run `30252925334` completed on 2026-07-27 with 29 independently retained site
artifacts. Compared with run `30250397882`, 11 sites advanced by 88,004 records.
New Zealand advanced by 26,000 records to 53,564 before the 1,800-second
deadline. Germany also advanced by 26,000. Five zero-record inventories were
complete and 24 targets remained fail-closed.

Eight targets ended on page-level HTTP 400 responses; the remainder primarily
ended on connection, TLS, gateway, or deadline failures. These observations
come from the retained manifests and retrieval evidence. They motivate cursor
pagination but do not establish percentage coverage of any national corpus.
- Ruff lint and format checks: passed.
- Actionlint: passed.
- Zizmor at medium severity: no findings (three configured suppressions).

The track remains open pending a hosted continuation from the merged workflow.
