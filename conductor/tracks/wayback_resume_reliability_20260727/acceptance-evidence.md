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
  targeted retry selector is now available for named sites; the existing
  weekly schedule still dispatches the complete matrix.

## Targeted retry control

Manual dispatches of `foi_site_internet_archive.yml` now accept an optional
`site_id`. Enumeration filters to that configured site and rejects unknown
identifiers; scheduled runs leave the input empty and retain the full 29-site
matrix. Regression tests cover both selection and unknown-site rejection.

Validation performed from downloaded artifacts in
`C:\tmp\fyi-archive-cursor-30262962651-all-2`: all 29 manifests were parsed;
top-level pagination mode, complete/fail-closed state, per-site record counts,
retrieval failures, and NZ progress were inspected. The track intentionally
remains open because 13 site acceptance criteria are not complete.

## Reconciliation update (2026-07-28)

Scheduled run `30339737294` retained exactly 29 independent artifacts: 22
complete and seven fail-closed, with 500,573 retained records. The incomplete
counts were AU 40,000; CA 54,000; DE 67,000; EU 56,000; NZ 50,000; UA 42,000;
and GB/UK 26,000. NZ remains incomplete; no percentage is inferred because no
defensible national denominator exists.

Bounded targeted follow-up produced AU run `30365391104` (complete, 63,473
records) and UA run `30365404274` (incomplete at 50,000 after HTTP 503). UK
retry `30369505285` was cancelled after a stale snapshot. Invalid selector
attempts (`30370087242`, `30370285224`, `30370349930`, `30370464238`) failed
closed during enumeration; valid CA run `30370646140` remained active without
a terminal update during the bounded observation window and was not retried
indefinitely. These runs do not establish corpus coverage.

Acceptance remains open: CA, DE, EU, NZ, UK, and UA are not all complete. They
resume on the existing weekly schedule; targeted dispatch remains an optional,
operator-controlled improvement rather than an unbounded retry loop.

## Targeted-run reliability hardening (2026-07-29)

The cancellation pattern came from dispatching separate runs into the workflow's
deliberate global concurrency group. A new optional comma-separated `site_ids`
input selects one bounded matrix, retaining the global serialization and
`max-parallel: 2` limit. The legacy singular `site_id` input remains supported.
Selection rejects mixed, empty, duplicate, and unknown targets and reports the
configured ids before any acquisition begins.

Long CDX calls now emit minute-level process heartbeats and checkpoint counts.
Checkpoint messages include only the SHA-256 of a next resume key, never the raw
key. Transient requests may use up to 32 attempts with a 60-second backoff cap,
still bounded by the existing whole-pattern deadline and fail-closed semantics.

Local verification: 394 tests passed and 1 skipped. Ruff preview lint, ty,
Actionlint, and Zizmor at medium severity all passed. The hosted multi-site
evidence requirement is reconciled below; completion still depends on the
inventories reaching terminal pagination.

## Bounded multi-site continuation 30373774064

Run `30373774064` exercised the merged `site_ids` control for
`ca-federal-atip,de-fragdenstaat,eu-asktheeu,nz-fyi,ua-dostup,uk-wdtk`.
Enumeration passed, the matrix kept at most two acquisition jobs active, no job
was cancelled, and exactly six independently retained site artifacts were
available when the run terminated fail-closed.

All six `manifest.json` files declare top-level
`pagination.mode=resume_key`. Every retrieval is explicitly incomplete with a
deadline failure, `pagination_complete=false`, a non-empty next resume key, and
`resumable=true`. Recomputing all 433 retained page fingerprints succeeded with
no duplicates. The independently reconstructed configuration SHA-256 matched
the checkpoint and retrieval values for every site, and page, checkpoint,
retrieval, and manifest record counts agreed.

| Site | Run 30252925334 | Run 30339737294 | Run 30373774064 | Delta from 30339737294 |
| --- | ---: | ---: | ---: | ---: |
| `ca-federal-atip` | 18,255 | 54,000 | 81,000 | +27,000 |
| `de-fragdenstaat` | 46,000 | 67,000 | 87,000 | +20,000 |
| `eu-asktheeu` | 18,084 | 56,000 | 80,000 | +24,000 |
| `nz-fyi` | 53,564 | 50,000 | 74,000 | +24,000 |
| `ua-dostup` | 7,149 | 42,000 | 63,000 | +21,000 |
| `uk-wdtk` | 18,000 | 26,000 | 48,000 | +22,000 |
| **Selected-site aggregate** | **161,052** | **295,000** | **433,000** | **+138,000** |

The older comparison run `30252925334` retained 218,554 records across its full
29-site matrix; its same-six subset retained 161,052. The current targeted run
retained 433,000 across only the six selected sites, a same-site increase of
271,948. The full-matrix and selected-site aggregates are deliberately not
treated as interchangeable.

New Zealand retained 74,000 records: 24,000 more than the immediately preceding
weekly checkpoint and 20,436 more than run `30252925334`. This is observed
checkpoint progress, not percentage coverage; no defensible national
denominator is available.

The completed logs contain six `cdx-start` events, 138 checkpoint events, and
186 minute-level heartbeat events. Every checkpoint log entry used
`next_resume_key_sha256`; searching for each artifact's raw next resume key
found zero log disclosures.

Acceptance remains open because none of the six selected inventories completed.
CA, DE, EU, NZ, UA, and UK resume on the existing weekly schedule. A separate
operator-controlled improvement is one bounded multi-site retry using the
workflow's allowed 2,400-second maximum; it is not an automatic or unbounded
retry loop.

## Operator-controlled continuation 30382291280

The single recommended follow-up ran from merged `main` with
`max_runtime_seconds=2400`, `resume_run_id=30373774064`, and the same six
selected site ids. The matrix retained exactly six independent artifacts with
no cancellation and never exceeded two active acquisitions.

EU and UA reached terminal pagination and are now complete. CA, DE, NZ, and UK
advanced before failing closed at the bounded deadline:

| Site | Run 30373774064 | Run 30382291280 | Delta | Result |
| --- | ---: | ---: | ---: | --- |
| `ca-federal-atip` | 81,000 | 117,000 | +36,000 | incomplete, resumable |
| `de-fragdenstaat` | 87,000 | 111,000 | +24,000 | incomplete, resumable |
| `eu-asktheeu` | 80,000 | 96,698 | +16,698 | complete |
| `nz-fyi` | 74,000 | 119,000 | +45,000 | incomplete, resumable |
| `ua-dostup` | 63,000 | 68,801 | +5,801 | complete |
| `uk-wdtk` | 48,000 | 77,000 | +29,000 | incomplete, resumable |
| **Selected-site aggregate** | **433,000** | **589,499** | **+156,499** | |

Every manifest declares top-level `pagination.mode=resume_key` and records
`30373774064` as its resume source. Recomputing all 590 retained page
fingerprints succeeded without duplicates. Independently reconstructed
configuration SHA-256 values matched every checkpoint and retrieval record, and
all page, checkpoint, retrieval, and manifest counts agreed. The two complete
exports also matched their recorded response SHA-256 values. Each incomplete
artifact retained a non-empty next resume key with `resumable=true`; complete
artifacts retained no next key and declare `resumable=false`.

The run logs contain six start events, 157 checkpoint events, and 185
minute-level heartbeats. All checkpoint log records used resume-key SHA-256
values, and none of the four retained raw next keys appeared in the logs.

New Zealand now retains 119,000 observed records, 45,000 more than the preceding
targeted run and 65,436 more than run `30252925334`. No percentage coverage is
inferred because no defensible national denominator exists.

The track remains open for CA, DE, NZ, and UK. These four sites resume through
the existing weekly schedule. The one recommended bounded follow-up has been
executed; no additional targeted retry loop is authorized or planned.
