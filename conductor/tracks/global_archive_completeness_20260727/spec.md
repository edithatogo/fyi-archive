# Specification: global archive completeness

## Objective

Make every configured FOI site independently preservable from its public
primary surface, the Internet Archive, and additional verified web archives,
with transparent provenance and transformation evidence.

## Requirements

- Build one normalized source graph spanning all configured sites and all 42
  jurisdiction targets without erasing the source registries from which it was
  derived.
- Treat origin capture, Internet Archive discovery, Internet Archive capture,
  replay verification, and durable publication as distinct evidence states.
- Replace planning-horizon percentages with enumerated public denominators
  whenever an authoritative enumeration is available.
- Preserve input hashes, transformation identity, output hashes, excluded
  synthetic records, and classified gaps.
- Make safe, public, read-only acquisition autonomous once deterministic
  readiness checks pass. Keep privacy, rights, credentials, and publication
  fail-closed.
- Retrieve complete, checkpointed Internet Archive inventories for every site
  and retain incomplete evidence without reporting it as complete.
- Record candidate national and independent archives for redundancy and
  verification without claiming availability before a source-specific probe.

## Acceptance

- All 29 site identities and 42 jurisdiction targets reconcile in the source
  graph.
- Completeness reports distinguish primary, Internet Archive, and redundant
  archive coverage and exclude synthetic rows from the primary numerator.
- Scheduled Internet Archive jobs use fail-closed complete pagination, retain
  per-page checkpoints, and emit provenance manifests.
- Repository documentation explains denominators, transformations, exclusions,
  limitations, and the operational path to 100% public coverage.
- Focused and full repository quality gates pass.
