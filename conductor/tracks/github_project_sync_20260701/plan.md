# Plan: github_project_sync_20260701

## Phase 1: Define the project model

- [x] 1.1 Confirm the repo project exists at `projects/4` and is linked to `fyi-archive`.
- [x] 1.2 Record the RIOPA umbrella scope and the source project boards in the track spec.
- [x] 1.3 Set the umbrella project description/readme to explain the mirroring model.

## Phase 2: Add the mirror mechanism

- [x] 2.1 Add a repo script that collects issue / PR URLs from the source boards.
- [x] 2.2 Add idempotent writes so the umbrella project only receives missing items.
- [x] 2.3 Add dry-run output that reports source counts, target counts, and gaps.

## Phase 3: Automate and verify

- [x] 3.1 Add a GitHub Actions workflow for scheduled and manual syncs.
- [x] 3.2 Run a one-time backfill into the RIOPA umbrella project.
- [x] 3.3 Verify the umbrella board matches the mirrored source items after sync.
