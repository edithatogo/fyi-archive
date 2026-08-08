# Live projection acceptance evidence

Run date: 2026-07-22

Input capture:

- Source revision: `live-probe-final-29825714444`
- Manifest: `.tmp/live-probe-final-29825714444/historical-backfill-10-10/manifests/latest_manifest.json`
- Process events: `.tmp/live-probe-final-29825714444/historical-backfill-10-10/dist/process-events/events.jsonl`
- Source: `https://fyi.org.nz/`

Command:

```text
fyi-archive process project --events .../events.jsonl --manifest .../latest_manifest.json --snapshot-revision live-probe-final-29825714444 --output-dir .../projection-current
fyi-archive process verify --output-dir .../projection-current
```

Observed coverage:

- `case_count`: 1
- `event_count`: 2
- `manifest_request_count`: 1
- `request_count_reconciles`: true
- `retracted_event_count`: 0
- `attachment_count`: 0 in the original process-event export; the corrected sidecar-aware export below records 1 attachment and reconciles it to the manifest.
- `verify`: true

This is a representative live adapter/projection check, not evidence that the
full archive corpus has been backfilled or that production publication is
authorized.

## Sidecar attachment continuation acceptance

The captured live probe `live-probe-final-29825714444` was exported through the
updated fyi-cli sidecar-aware process exporter. The resulting projection
benchmark completed with:

- 1 request/case;
- 2 process events;
- 1 attachment;
- request and attachment reconciliation both `true`;
- verified projection checksum manifest;
- publication `none`.

This closes the live vertical-slice attachment gate. It does not represent the
full 33,217-request public deposit, whose process log remains a separate
backfill gate.
