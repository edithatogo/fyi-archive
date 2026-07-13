# Maintenance hardening

## Goal

Keep repository documentation, operational state, dependency resolution, and
quality-gate outcomes trustworthy as the archive grows.

## Scope

- Correct user-facing setup and generic project metadata.
- Refresh stale operational snapshots without fabricating live mirror evidence.
- Make local quality commands fail when a required check fails.
- Pin the upstream capture dependency to a published release.
- Re-drive pending historical batches when dispatch is complete and no workers
  are active, while preserving serial and bounded operation.

## Non-goals

- No new network capture mechanism.
- No change to source-site politeness defaults.
- No automatic production publication or DOI release.
