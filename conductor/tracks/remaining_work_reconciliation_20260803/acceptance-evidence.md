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
- PR #332 is merged (`2874ba2`) after all required Python quality, repository
  quality, Codecov, and CodeQL checks passed. The former queued-CI blocker is
  resolved; no bypass or retry loop was used.

## Open acceptance gates

- Wayback partition acquisition has not yet produced an accepted complete trial.
  CA, DE, and UK remain resumable on the weekly schedule.
- Dedicated `RIOPA_PROJECT_TOKEN` is absent. Fallback project sync is operational;
  least-privilege hardening remains optional.
- No percentage coverage claim is made without a defensible national denominator.
