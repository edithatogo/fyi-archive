# Project Tracks

Registry of all tracks for the project. Each track has its own folder with `spec.md`
+ `plan.md` (+ `metadata.json`). Requirements traceability lives in
[`requirements.md`](./requirements.md); design in [`design.md`](./design.md).

## Status Key

- `[ ]` — pending
- `[~]` — in progress
- `[x]` — complete / evidence-backed
- `[!]` — blocked

## Dependency legend

- `fyi-cli: <track>` — a capability track in the companion `fyi-cli` repo that must
  land before this track's orchestration can function.

---

## Foundation tracks

### [x] Track: Repo bootstrap
Track ID: `repo_bootstrap_20260627` — satisfies **R-07, R-11, R-12**
Goal: Stand up the standalone `fyi-archive` git repo, remote, full root scaffolding, conductor setup (incl. MoSCoW requirements + Mermaid design), quality tooling, README, and wire it as a workspace submodule.
Link: [./tracks/repo_bootstrap_20260627/](./tracks/repo_bootstrap_20260627/)

### [x] Track: CI/CD foundation
Track ID: `ci_cd_foundation_20260627` — satisfies **R-15, R-18**
Goal: tests.yml + code_quality.yml (uv --frozen matrix, ruff, ty, pytest+cov, version-consistency) + codeql/scorecard/docs/mirror_sync/ci-learning-candidates.
Link: [./tracks/ci_cd_foundation_20260627/](./tracks/ci_cd_foundation_20260627/)

### [x] Track: Code quality gates
Track ID: `code_quality_gates_20260627` — satisfies **R-18**
Goal: ruff (family ruleset), ty strict, pytest+coverage ramp, hypothesis property tests, pre-commit, vulture/deptry hygiene, `make quality` parity with CI.
Link: [./tracks/code_quality_gates_20260627/](./tracks/code_quality_gates_20260627/)

### [x] Track: Security & supply chain
Track ID: `security_supply_chain_20260627` — satisfies **R-18, R-24**; provides **R-26**
Goal: CycloneDX SBOM per release, build-provenance attestations, CodeQL + Scorecard, secret-validation workflows, optional Sigstore.
Link: [./tracks/security_supply_chain_20260627/](./tracks/security_supply_chain_20260627/)

### [x] Track: Versioning & releases
Track ID: `versioning_releases_20260627` — satisfies **R-16**
Goal: `release-please` dynamic SemVer + CHANGELOG + GitHub Releases from Conventional Commits; version-consistency gate; annual Zenodo DOI snapshot link.
Link: [./tracks/versioning_releases_20260627/](./tracks/versioning_releases_20260627/)

---

## Archive tracks (historical → prospective)

### [x] Track: Historical-seed orchestration
Track ID: `historical_seed_orchestration_20260627` — satisfies **R-01, R-02, R-03, R-13, R-20, R-21**
Goal: Resumable, date-windowed, capped historical backfill driving `fyi-cli` capture; assemble initial manifest; capped smoke seed.
Depends on: fyi-cli `bulk-site-enumeration`, `faithful-archive-capture`.
Link: [./tracks/historical_seed_orchestration_20260627/](./tracks/historical_seed_orchestration_20260627/)

### [x] Track: Prospective sync orchestration
Track ID: `prospective_sync_orchestration_20260627` — satisfies **R-14**
Goal: Daily content-addressed incremental sync → HF, with restore → diff → capture-new → manifest → upload → SHA-256 verify.
Depends on: fyi-cli `archival-content-diff`; this repo's `historical_seed_orchestration`.
Link: [./tracks/prospective_sync_orchestration_20260627/](./tracks/prospective_sync_orchestration_20260627/)

---

## Distribution & observability tracks

### [x] Track: Multi-mirror publish
Track ID: `multi_mirror_publish_20260627` — satisfies **R-08, R-09, R-10, R-22, R-25**
Goal: HF (live) + Zenodo (annual DOI, draft-first, gated) + OSF (project + components); Croissant/Frictionless metadata; DuckDB export; SBOM + provenance.
Link: [./tracks/multi_mirror_publish_20260627/](./tracks/multi_mirror_publish_20260627/)

### [x] Track: Observability & quality
Track ID: `observability_quality_20260627` — satisfies **R-19, R-23**; supports **R-27**
Goal: `fyi-archive doctor` (freshness, coverage gaps, mirror parity); metadata parity CI; fyi-cli version-pin test; coverage ramp.
Depends on: fyi-cli `archive-health-doctor`.
Link: [./tracks/observability_quality_20260627/](./tracks/observability_quality_20260627/)

### [x] Track: GitHub project mirror and RIOPA sync
Track ID: `github_project_sync_20260701`
Goal: Mirror the `fyi-archive` repo project and sibling repo boards into the RIOPA umbrella project with a verifiable item-level sync and scheduled automation.
Link: [./tracks/github_project_sync_20260701/](./tracks/github_project_sync_20260701/)

### [x] Track: GitHub project best practices and workflow maximization
Track ID: `github_project_best_practices_20260701`
Goal: Maximize GitHub Projects v2 best practices, native workflows, views, and GraphQL automation while keeping custom code limited to cross-project sync.
Link: [./archive/github_project_best_practices_20260701/](./archive/github_project_best_practices_20260701/)

---

## Companion capability tracks (in fyi-cli)

These live in `fyi-cli`'s `.conductor/` and are prerequisites for the archive tracks
above. They are the "improving and adding features" to `fyi-cli` that the user's brief
calls for (R-05). Registered there in parallel.

| fyi-cli track | enables (fyi-archive track) | satisfies |
| --- | --- | --- |
| `bulk-site-enumeration` | historical_seed_orchestration | R-01, R-20 |
| `faithful-archive-capture` | historical_seed_orchestration | R-01, R-02 |
| `archival-content-diff` | prospective_sync_orchestration | R-14 |
| `archive-health-doctor` | observability_quality | R-23 |
| `cross-worker-rate-limiter` | archive discovery and backfill jobs with bounded aggregate pacing | safer concurrent request rate across workers; archived in [./archive/cross_worker_rate_limiter_20260701/](./archive/cross_worker_rate_limiter_20260701/) |

## Archived dependency tracks

### [x] Track: Cross-worker rate limiter
Track ID: `cross_worker_rate_limiter_20260701`
Goal: Ensure the sibling `fyi-cli` repo provides a shared cross-worker limiter or shared backoff mechanism so concurrent archive discovery and sync jobs bound aggregate request rate, not just per-process pacing.
Link: [./archive/cross_worker_rate_limiter_20260701/](./archive/cross_worker_rate_limiter_20260701/)

---

## Explicit non-goals (this phase) — see requirements R-03, R-04, R-28, R-29

- Analysis, OCR, text extraction, entity normalisation.
- Full-text search index / serving API over the archive.
- Write/submit operations against fyi.org.nz.
- Reimplementation of capture logic inside `fyi-archive` (it belongs in `fyi-cli`).
