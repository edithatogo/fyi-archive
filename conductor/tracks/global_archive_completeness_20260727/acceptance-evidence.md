# Acceptance evidence: global archive completeness

Date: 2026-07-27

## Requirement traceability

| Requirement | Evidence |
| --- | --- |
| Normalize all sites and targets | `configs/archive_source_graph.json`, `src/fyi_archive/source_graph.py`, and `tests/test_source_graph.py` reconcile 29 sites and 42 jurisdiction targets exactly once. |
| Separate preservation states | The normalized graph distinguishes primary status, complete Wayback CDX discovery, prospective Archive-It/equivalent capture, source probing, and durable handoff. |
| Enumerated denominators | `doctor.get_coverage_info` prefers per-instance or global enumerated public denominators and labels the legacy ID horizon as a planning estimate. |
| Transparent transformation | Both transformations emit stable IDs, input SHA-256 values, deterministic payload hashes, duplicate counts, explicit synthetic exclusions, and URL-level gaps. |
| Autonomous bounded capture | Read-only CDX exports are scheduled; live origin capture uses repository readiness variables, rate/runtime caps, local windows, and the existing AU protected environment. Publication, credentials, rights, privacy, and signing remain fail-closed. |
| Complete Wayback inventories | The 29-site workflow uses complete paginated CDX acquisition, checkpoint retention, optional compatible resume, `always()` evidence upload, and a final fail-closed completeness check. |
| Independent redundancy | Internet Archive, Common Crawl, Arquivo.pt, Archive-It, and applicable national archives are registered with explicit configured/candidate states. |

## Verification receipts

- `uv run python scripts/build_archive_source_graph.py --check --output C:/tmp/fyi-archive-source-graph.json`
  - sites: 29
  - jurisdiction targets: 42
  - deterministic payload SHA-256: `f1a636dc8c3c56f6f9bc1a03033cc354cdd533b1e4b9ab7df2640ecc5bf94e63`
- Focused archive/workflow tests: `31 passed`.
- Full test suite: `353 passed, 1 skipped`.
- Ruff lint: passed for `src`, `tests`, and `scripts`.
- Ruff format: all nine newly added Python files pass.
- `ty check src`: passed.
- `actionlint` on all five changed workflows: passed.
- Focused security-diff review: no reportable finding. The review identified
  missing scheduled-input defaults in the new monthly all-captures workflow;
  defaults were added and revalidated.

## Open baseline limitation

The repository-wide `ruff format --check src tests scripts` gate still reports
32 pre-existing files from `origin/main` that would be reformatted. None is a
file introduced by this track. They are intentionally not rewritten in this
feature diff; a separate mechanical formatting change should address that
baseline without obscuring archive logic review.

## Operational truth

This implementation configures discovery and acquisition machinery. It does
not claim that a country is already 100% archived. A site reaches that state
only when an enumerated public denominator and completed source inventories
produce a reconciliation receipt at 100%. GitHub artifacts are staging
evidence, not durable publication. Internet Archive CDX presence is historical
discovery, not proof of prospective capture; Archive-It or an equivalent
collection crawl remains required for that assurance.
