# Track: CI/CD foundation
Track ID: `ci_cd_foundation_20260627`
Satisfies: **R-15** (entirely automated), **R-18** (cicd, code quality, checks).

## Goal

Establish the CI/CD backbone every other track depends on: test + quality gates on
push/PR, plus the supporting security/docs/mirror/learning workflows. Mirrors the
family pattern (`corpus-cases-medilegal-nz`, `corpus-law-nz`).

## Scope

- `tests.yml` — push/PR; uv `--frozen`; matrix Python 3.12 + 3.14; `ruff check` +
  `ruff format --check`; `pytest --cov`; `scripts/check_version_consistency.py`.
  (3.14 continues-on-error, matching family.)
- `code_quality.yml` — ruff, `ty` typecheck, typos, taplo, actionlint, zizmor
  (`--min-severity medium`).
- `codeql.yml` — Python CodeQL (weekly cron + push/PR).
- `scorecard.yml` — OpenSSF Scorecard (publishes SARIF).
- `docs.yml` — markdown/vale docs check.
- `mirror_sync.yml` — push to secondary git mirror via SSH (gated on `GIT_MIRROR_URL`).
- `ci-learning-candidates.yml` — record CI failures into
  `conductor/improvement-backlog.md`.
- Workflow `permissions:` locked to `contents: read` by default (publish workflows
  opt up).

## Out of scope

- The data workflows (`historical_seed`, `hf_sync`, `publish_archives`) — separate
  tracks. The release workflow — `versioning_releases`.

## Acceptance criteria
- [x] `tests.yml` green on a no-op push; matrix 3.12/3.14; coverage reported.
- [x] `code_quality.yml` enforces ruff + ty + typos + taplo + actionlint + zizmor.
- [x] `check_version_consistency.py` is a required gate.
- [x] `codeql` + `scorecard` run and publish results.
- [x] All workflows pass `actionlint` and `zizmor` clean.
- [x] Least-privilege `permissions:` declared on every workflow.

## Risks

- Family tools (`ty`, `taplo`, `actionlint`, `zizmor`) versions drift → Renovate keeps
  them current; CI is authoritative.
- OneDrive path quirks → CI runs on GitHub-hosted runners, unaffected.
