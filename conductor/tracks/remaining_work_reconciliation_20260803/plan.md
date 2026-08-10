# Implementation plan

- [x] Reconcile the registry against `origin/main` and identify open tracks and
  hosted gates.
- [x] Record project-sync run `30736460096`: 683 mirrored, 217 missing, fallback
  `WORKFLOW_PAT`, no credential value exposed.
- [x] Record bounded NZ failure `30752216738` as fail-closed; do not retry it
  automatically.
- [x] Preserve the merged `max_auto_batches=20` cap for chained NZ continuation.
- [x] Preserve the canonical Hugging Face dataset at 33,217 records; no delete or
  rewrite action is authorized.
- [x] Record the Hugging Face metadata-only correction as provider-gated after
  HTTP 403 on upload and PR creation.
- [x] Resolve the documentation/Conductor CI blocker through PR #332; required
  Python quality, repository quality, Codecov, and CodeQL checks all passed and
  the squash merge landed as `2874ba23490e63ae5b1ae21bca675e6aa214188d`.
- [x] Dispatch exactly one bounded named-site partition-trial candidate:
  `ca-federal-atip`, run `30755229752`, reusing run `30391530911` checkpoints,
  with a 7,200-second ceiling and no automatic follow-up.
- [x] Verify the bounded candidate's complete evidence bundle: one retained CA
  artifact, 285,237 records, 286 pages, resume-key mode, config hash
  `1e3a3398...ae9b8`, no failures, and no remaining resume key.
- [ ] Exercise the separate time-partition acquisition and complete-only merge
  path; the candidate above was a complete cursor inventory, not a partition
  plan merge.
- [x] Run the local partition planner/merge regression suite against the current
  implementation: `tests/test_wayback_partitions.py` and
  `tests/test_wayback_evidence.py` passed (44 tests). This validates the local
  guardrails but does not substitute for hosted partition acquisition.
- [x] Add bounded workflow inputs for `from_timestamp`, `to_timestamp`, and
  `include_urlkey`, with validation and pass-through to the fetcher so a future
  named-site partition trial can produce mergeable evidence.
- [x] Reconcile partition candidate `31388750483`: CA 2020-2024 failed closed
  after 25 pages (`record_count=25,000`) on whole-run deadline exhaustion; its
  checkpoint retained a resume key and no partial success was published.
- [ ] Reconcile the trial result: close only if all required partition and merge
  criteria pass; otherwise retain the track open and document weekly resumption.
- [ ] Optionally provision `RIOPA_PROJECT_TOKEN` with least privilege; fallback
  project sync is already operational, so this is not an emergency action.
- [ ] Reassess open product tracks independently; do not mark unrelated tracks
  complete merely because this closure ledger exists.

## Stop conditions

Stop and document the blocker when provider authorization, repository secrets,
source availability, or a defensible denominator is absent. Never compensate by
deleting data, broadening tokens, or dispatching an unbounded retry loop.
