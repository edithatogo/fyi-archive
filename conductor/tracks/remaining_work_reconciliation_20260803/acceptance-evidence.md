# Acceptance evidence

## Completed

- `origin/main` reconciled at `cdffc74`.
- Project sync `30736460096` succeeded through the fallback `WORKFLOW_PAT`:
  683 items mirrored, 217 missing, and a Project 4 status update posted.
- NZ continuation failure `30752216738` is recorded as fail-closed after one
  failed capture request. No automatic retry was dispatched.
- Chained NZ continuation is bounded by `max_auto_batches=20`.
- Canonical Hugging Face dataset integrity remains 33,217 records. No data was
  deleted or rewritten.
- Hugging Face metadata correction remains blocked by provider HTTP 403.
- PR #332 is merged after all required Python quality, repository
  quality, Codecov, and CodeQL checks passed. The former queued-CI blocker is
  resolved; no bypass or retry loop was used.
- Candidate run `30755229752` completed successfully for `ca-federal-atip`.
  Artifact inspection found exactly one retained complete artifact with 285,237
  records over 286 pages; manifest and retrieval both declare
  `pagination.mode=resume_key`, the configuration hash is
  `1e3a3398...ae9b8`, failures are empty, and `next_resume_key` is null.
  `scripts/verify_wayback_artifacts.py` independently returned one complete site
  and a null coverage percentage. This validates cursor acquisition, but it is
  not evidence of the separate time-partition merge path.

## Open acceptance gates

- Time-partition acquisition and complete-only merge have not yet produced an
  accepted trial. The cursor-inventory candidate is complete but insufficient
  for that distinct gate.
  CA, DE, and UK remain resumable on the weekly schedule.
- Dedicated `RIOPA_PROJECT_TOKEN` is absent. Fallback project sync is operational;
  least-privilege hardening remains optional.
- No percentage coverage claim is made without a defensible national denominator.
