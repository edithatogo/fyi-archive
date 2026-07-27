# Specification: Wayback resume reliability

## Evidence

Run `30241894770` retained evidence for all 29 registered sites, but 23 targets
failed closed after transient CDX transport errors, page-level HTTP 400
responses, or the whole-run deadline.
Automatic continuation run `30250397882` proved checkpoint restoration across
all 29 site artifacts. Twelve targets advanced by 34,674 records and 37 pages,
including New Zealand from 25,564 to 27,564 records. Six zero-record inventories
completed, while 23 remained fail-closed because of transport errors, malformed
responses, or the deadline. This evidence requires patient retries and reduced
request concurrency, without weakening completeness semantics.


## Requirements

- Retry observed transient page failures within the existing deadline.
- Restore the newest compatible per-site checkpoint automatically.
- Preserve an explicit resume run as the highest-priority override.
- Validate checkpoint configuration and hashes before continuing.
- Retry malformed or empty JSON responses with patient bounded backoff.
- Limit hosted CDX enumeration to two concurrent sites.
- Allow 1,800 seconds per URL pattern within the existing job timeout.
- Refresh from scratch when the newest compatible inventory is already complete.
- Keep site evidence separate and fail closed until pagination completes.
- Record the selected resume source in provenance.
- Never contact origin FOI sites or broaden GitHub token permissions.

## Acceptance criteria

- Focused retry and workflow-resume regression tests pass.
- Repository quality gates pass without weakening completeness semantics.
- A hosted continuation retains per-site evidence and demonstrates safe progress.
