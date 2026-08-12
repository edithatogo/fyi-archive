# Generic instance acquisition and continuation controller

Issue: [fyi-archive #370](https://github.com/edithatogo/fyi-archive/issues/370),
sub-issue of [#196](https://github.com/edithatogo/fyi-archive/issues/196).
Downstream: [foi-process #114](https://github.com/edithatogo/foi-process/issues/114).

## Goal

Replace duplicated country- and workflow-specific orchestration with one
instance-keyed pipeline. Preserve the active NZ backfill until a shadow run
proves exact operational and data parity.

## Ownership boundaries

- `fyi-cli` owns live-origin access, Internet Archive discovery and replay,
  request and attachment capture, WARC/WACZ creation, and process-event export.
- `fyi-archive` owns declarative instance configuration, scheduling, leases,
  checkpoints, immutable package assembly, validation, retention, and archive
  publication.
- `foi-process` consumes only pinned, checksummed `fyi-archive` packages and
  owns process mining, derived event-log publication, and dashboard assets.
- Hugging Face raw archive datasets and derived process datasets are distinct
  outputs with linked provenance and independent publication gates.

## Requirements

- One schema-validated registry is the source for runtime instance settings,
  source adapters, legal profiles, rate limits, storage targets, and status.
- The reusable controller accepts `instance_id`; country and jurisdiction are
  filtering/profile metadata rather than execution identities.
- Every handoff package declares schema version, instance, archive revision,
  takedown revision, source ordering, row and byte counts, file digests,
  provenance, retention status, and compatible downstream contract versions.
- Ordered deltas and periodic compacted snapshots are durable outside ephemeral
  Actions artifacts and reproduce the same state as full replay.
- Current direct CDX and replay network calls in `fyi-archive` are inventoried,
  then migrated behind a versioned `fyi-cli` adapter. They are not stopped until
  replacement parity and recovery behavior are demonstrated.
- NZ remains first. No other instance is promoted through this controller until
  NZ queue, capture, event, attachment, revision, lease, checkpoint, retry, and
  takedown behavior is equivalent.

## Non-goals

- No change to the active NZ lease chain in the planning increment.
- No jurisdiction publication approval.
- No merging of raw archive and derived process datasets.
- No claim that Internet Archive indexes substitute for captured request data.

## Acceptance

- Registry schema and uniqueness tests reject duplicate or incomplete entries.
- Reusable workflow tests prove per-instance isolation and fail-closed inputs.
- Network-boundary tests prevent new source HTTP clients in `fyi-archive`.
- Package contract and downstream compatibility fixtures pass in both repos.
- NZ shadow evidence proves exact parity before the legacy controller is retired.
- Retry, outage, stale-lease, partial-package, takedown, and rollback paths have
  tested recovery receipts.
