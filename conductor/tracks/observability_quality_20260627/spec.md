# Track: Observability & quality
Track ID: `observability_quality_20260627`

## Goal

Make the archive's health and the repo's quality visible and enforced: a `doctor`
command reporting freshness/coverage/mirror-parity, metadata-parity CI, a `fyi-cli`
version-pin test (so an upstream `fyi-cli` bump can't silently change capture
behaviour), and a coverage ramp.

## Prerequisites

- `fyi-cli` track `archive-health-doctor` (provides raw health signals this repo
  assembles into a parity report).

## Scope

- `fyi-archive doctor`: aggregates manifest counts, last-successful-sync, and the
  three mirror record counts into a parity report → GHA step summary + committed
  `conductor/archive_health.json`. (Model on `sm-govt-nz`'s
  `archive_health_monitor`.)
- `archive_health_monitor.yml`: scheduled health check that fails on drift.
- `tests/test_fyi_cli_version.py`: asserts the installed `fyi-cli` matches the pinned
  version in `pyproject.toml`; documents the manual-review requirement on bumps.
- `validate_metadata.yml` parity cross-check (HF vs Zenodo vs OSF counts).
- Coverage ramp: raise `[tool.coverage.report] fail_under` from 60 → 80 as modules
  land.

## Out of scope

- Health-signal computation internals (that's `fyi-cli`).

## Acceptance criteria

- [ ] `fyi-archive doctor` emits a parity report to stdout and writes
      `conductor/archive_health.json`.
- [ ] `archive_health_monitor.yml` fails on mirror-parity drift.
- [ ] `test_fyi_cli_version.py` fails if installed `fyi-cli` != pinned version.
- [ ] `validate_metadata.yml` fails on count mismatch between mirrors.
- [ ] `make test-cov` hits the current `fail_under` target.

## Risks

- Mirror counts legitimately diverge during publish windows → parity check tolerates a
  documented small skew window.
