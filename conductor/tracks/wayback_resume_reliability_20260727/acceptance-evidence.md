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

## Cursor continuation run 30262962651

- Hosted run terminal state: `failure` (13 matrix jobs failed closed); artifact
  boundary was nevertheless exactly 29 independently retained site artifacts.
- Every retained `manifest.json` declares top-level `pagination.mode` as
  `resume_key`. No artifact was accepted without that provenance marker.
- 16 manifests are complete and 13 are incomplete with explicit retrieval
  failures. The incomplete artifacts are `AU`, `BE`, `CA`, `CO`, `CZ`, `DE`,
  `EU`, `FR`, `HU`, `NL`, `NZ`, `UA`, and `GB`.
- Aggregate records retained in this run: 257,528. Complete-site records are
  observed directly in manifests; failed sites retain partial counts and are
  not treated as complete coverage.
- New Zealand (`nz-fyi`) retained 23,000 records in 23 pages before the
  whole-run deadline and is explicitly incomplete (`pagination_complete=false`)
  with a fail-closed CDX acquisition failure. No percentage coverage is
  inferred because no defensible national denominator exists.
- Compared with run `30252925334`, which recorded 88,004 additional records
  across 11 advancing sites and NZ at 53,564, this run is a fresh bounded
  continuation snapshot; per-site counts above are the authoritative retained
  observations and are not interpreted as a national corpus percentage.
- The 13 incomplete sites will resume on the existing weekly schedule. A
  targeted-run improvement is recommended separately: add an explicit site
  selector/resume-key input so only named incomplete sites can be retried
  without dispatching an unbounded matrix retry.

Validation performed from downloaded artifacts in
`C:\tmp\fyi-archive-cursor-30262962651-all-2`: all 29 manifests were parsed;
top-level pagination mode, complete/fail-closed state, per-site record counts,
retrieval failures, and NZ progress were inspected. The track intentionally
remains open because 13 site acceptance criteria are not complete.
