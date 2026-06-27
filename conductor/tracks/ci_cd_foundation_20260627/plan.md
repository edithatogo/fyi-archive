# Plan: ci_cd_foundation_20260627

## Phase 1: Test + quality gates
- [x] 1.1 `tests.yml` (uv --frozen, matrix 3.12/3.14, ruff, pytest+cov, version-check).
- [x] 1.2 `code_quality.yml` (ruff, ty, typos, taplo, actionlint, zizmor).
- [x] 1.3 `check_version_consistency.py` wired as a required gate in `tests.yml`.

## Phase 2: Security + docs + mirror
- [x] 2.1 `codeql.yml`, `scorecard.yml`.
- [x] 2.2 `docs.yml` (markdownlint + vale).
- [x] 2.3 `mirror_sync.yml` (gated on `GIT_MIRROR_URL`).

## Phase 3: Learning loop + hardening
- [x] 3.1 `ci-learning-candidates.yml` → `improvement-backlog.md`.
- [x] 3.2 Least-privilege `permissions:` audit across all workflows.
- [x] 3.3 actionlint + zizmor clean on the full set.
