# Specification: Wayback resume reliability

## Evidence

Run `30241894770` retained evidence for all 29 registered sites, but 23 targets
failed closed after transient CDX transport errors, page-level HTTP 400
responses, or the whole-run deadline.

## Requirements

- Retry observed transient page failures within the existing deadline.
- Restore the newest compatible per-site checkpoint automatically.
- Preserve an explicit resume run as the highest-priority override.
- Validate checkpoint configuration and hashes before continuing.
- Keep site evidence separate and fail closed until pagination completes.
- Record the selected resume source in provenance.
- Never contact origin FOI sites or broaden GitHub token permissions.

## Acceptance criteria

- Focused retry and workflow-resume regression tests pass.
- Repository quality gates pass without weakening completeness semantics.
