# Plan: observability_quality_20260627

## Phase 1: Doctor + health store

- [ ] 1.1 `fyi-archive doctor` subcommand: assemble freshness, coverage gaps, mirror
      parity from manifest + mirror record counts.
- [ ] 1.2 Write `conductor/archive_health.json`; render step summary in workflow.
- [ ] 1.3 `archive_health_monitor.yml` scheduled check.

## Phase 2: Version pin + parity CI

- [ ] 2.1 `tests/test_fyi_cli_version.py` asserts installed == pinned `fyi-cli`.
- [ ] 2.2 `validate_metadata.yml` parity cross-check (HF/Zenodo/OSF counts) with a
      documented skew tolerance.

## Phase 3: Coverage ramp

- [ ] 3.1 As real modules land, raise `fail_under` 60 → 70 → 80.
- [ ] 3.2 Add hypothesis property tests for manifest/diff/sync-state invariants.

## Dependencies

- BLOCKED on `fyi-cli` track `archive-health-doctor` for raw signals.
- Parity CI benefits from `multi_mirror_publish` being functional.
