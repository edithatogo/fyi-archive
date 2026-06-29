# Plan: code_quality_gates_20260627

## Phase 1: Lint + types
- [x] 1.1 Confirm ruff family ruleset active; `make lint format typecheck` green.
- [x] 1.2 `ty` strict on `src/`; document any rule relaxations.

## Phase 2: Tests + coverage ramp
- [x] 2.1 pytest markers wired; `make test-cov` reports coverage.
- [x] 2.2 Hypothesis property test for a core invariant (e.g. canonical-hash stability).
- [x] 2.3 Coverage ramp plan 60 → 70 → 80 recorded in `maturity-checklist.md`.

## Phase 3: Hygiene + make surface
- [x] 3.1 `vulture` + `deptry` `make` targets; advisory CI step.
- [x] 3.2 `make quality` parity with CI verified.
- [x] 3.3 pre-commit installed + documented in README.
