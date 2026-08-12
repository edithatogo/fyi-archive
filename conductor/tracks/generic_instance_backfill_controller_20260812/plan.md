# Plan

## Phase 1: Contract and inventory

- [ ] Inventory every live-source, Internet Archive, artifact-download, and
  publication network path; classify each by owning repository.
- [ ] Define the versioned instance-registry and handoff-package schemas.
- [ ] Add contract fixtures shared with `fyi-cli` and `foi-process`.
- [ ] Record the current NZ workflow/run/state baseline without changing it.

## Phase 2: Registry consolidation

- [ ] Move executable instance settings and legal/profile metadata into one
  schema-validated declarative registry.
- [ ] Generate Python runtime objects and workflow matrices from that registry.
- [ ] Add uniqueness, URL, rate-limit namespace, storage-target, and status tests.

## Phase 3: Source adapters

- [ ] Add or extend versioned `fyi-cli` adapters for live discovery/capture and
  Internet Archive CDX/replay discovery.
- [ ] Replace direct `fyi-archive` source-network calls only after fixture and
  hosted shadow parity is green.
- [ ] Enforce the network ownership boundary in CI.

## Phase 4: Generic controller

- [ ] Generalise lease/checkpoint/requeue state from NZ offsets to instance jobs.
- [ ] Add a reusable `workflow_call` capture workflow and one registry scheduler.
- [ ] Preserve bounded concurrency, health gates, failure artifacts, and
  evidence-backed lease release per instance.

## Phase 5: Durable handoff

- [ ] Assemble immutable packages with manifests, process-event and attachment
  sidecars, checksums, provenance, coverage, and takedown revisions.
- [ ] Publish ordered deltas and periodic compacted snapshots to durable archive
  storage; treat Actions artifacts as receipts, not the sole data plane.
- [ ] Validate the package in `foi-process` before mining or publication.

## Phase 6: NZ shadow and cutover

- [ ] Run the generic controller beside the active NZ controller over the same
  bounded ranges without duplicate source load.
- [ ] Require exact queue/case/event/attachment/revision/checkpoint parity and
  equivalent retry and takedown behavior.
- [ ] Cut over NZ only after hosted evidence is linked to #370 and #196; retain
  a documented rollback window.

## Phase 7: Next instance

- [ ] Select the next archive instance from evidence-backed readiness, not a
  country loop.
- [ ] Require source rights, retention, removal, threat-model, and publication
  decisions for that instance before promotion.
- [ ] Keep capture approval separate from public archive and process publication.
