# Learning Log

Short, dated entries capturing non-obvious findings during work.

## 2026-06-27
- **fyi.org.nz API shape:** reads need no auth; append `.json` to most URLs;
  `/request/{id}.json` 302-redirects to `/request/{url_title}.json` (follow
  redirects). Bulk enumeration is via advanced-search Atom feeds + their `.json`
  equivalents — there is no `list.json`. → Drives the `bulk-site-enumeration`
  capability in `fyi-cli`.
- **fyi-cli cannot enumerate the site today:** it only fetches a single request by ID
  and reads feeds. The full-site archive therefore requires *new* `fyi-cli`
  capabilities (enumeration, WARC/WACZ capture, diff, health), not a reimplementation
  inside `fyi-archive`.
- **Token availability:** `HF_TOKEN`, `OSF_TOKEN`(+user/pass), `ZENODO_TOKEN`,
  `ZENODO_SANDBOX_TOKEN`, `GITHUB_TOKEN` present locally in the workspace `.env`.
  `osfclient`/`zenodo-client` not installed → use raw `requests` (matches siblings).
- **Conductor path quirk:** `fyi-cli` uses `.conductor/` (leading dot); this repo and
  the corpus siblings use `conductor/`.

## 2026-07-09
- **Conductor reconcile:** historical_seed and prospective_sync metadata were stale
  (`blocked` / `in_progress`) while plans and tracks.md already showed complete.
  setup_state still said phase=setup with track_count=9. Corrected to
  storage_operations / 10 tracks + archived list; maturity checklist refreshed
  against GHA smoke evidence.
- **Branch divergence:** local `codex/max-parallel-3-backfill` was 15 ahead / 78
  behind origin after PR #26 landed on main with rewritten history. Prefer reset
  onto `origin/main` and re-apply intentional WIP rather than merging the parallel
  history. Stashed workflow pin/max-batch rewrites looked regressive vs main and
  were discarded; project-sync / CODEOWNERS-adjacent untracked work was kept.
- **archive_health.json is gitignored:** monitor still writes it as a job artifact;
  do not treat a zero local copy as the live operational truth without checking
  issue #9 backfill state + recent GHA runs.
- **Live backfill (issue #9, decoded state):** ~33 244 captured records; next_id
  142 501; dispatch range completed through 250 000; 2 879 merged batches with
  195 pending as of state `updated_at` 2026-07-07. Controllers still tick on main
  (successful runs through 2026-07-09). HF/OSF/Zenodo mirror counts in the latest
  health monitor remain 0 — capture is ahead of mirror population.
- **Merge stall diagnosis:** controller plan is `complete: true` /
  `planned_count: 0` once `dispatch_next_id > id_to`, so it never re-merges
  leftover pending rows. On 2026-07-07 a burst of concurrent merge dispatches was
  cancelled; PRs #31/#32 serialize merges going forward. Pending rows only store
  `controller_run_id` + label (no `worker_run_id`). Ops procedure:
  `docs/backfill-ops-runbook.md`.
