# Track: Code quality gates
Track ID: `code_quality_gates_20260627`
Satisfies: **R-18** (code quality, checks).

## Goal

Define and enforce the project's code-quality standard: lint, types, tests, coverage,
property tests, and dependency/dead-code hygiene — at parity with the most mature
family repos.

## Scope

- `ruff` config (already in `pyproject.toml`; family ruleset) enforced in CI + pre-commit.
- `ty` strict type checking on `src/`.
- `pytest` + `pytest-cov` (`fail_under = 60`, ramp target documented); markers
  `unit/integration/smoke/hypothesis`.
- `hypothesis` property tests for invariants (manifest hashing, diff
  classification, ledger parsing).
- `pre-commit` (ruff + typos + markdownlint) installed and documented.
- `vulture` (dead code) + `deptry` (dependency hygiene) as `make` targets + advisory CI.
- `make quality` as the single local command mirroring CI.

## Out of scope

- The workflow *files* (those land in `ci_cd_foundation`); this track owns the
  *configuration* and the `make` surface.

## Acceptance criteria
- [x] `make quality` runs the full gate locally and matches CI.
- [x] `ruff check` + `ruff format --check` clean on `src/ tests/ scripts/`.
- [x] `ty check src` clean.
- [x] `pytest --cov` passes the current `fail_under`; coverage target ramp documented.
- [x] At least one hypothesis property test exists for a core invariant.
- [x] `vulture` + `deptry` run without blocking errors.

## Risks

- `ty` strictness on stubs → relax specific rules with documented justification only.
