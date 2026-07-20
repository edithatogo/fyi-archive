# Project Tracks

Registry of all tracks for the project. Each track has its own folder with `spec.md`
+ `plan.md` (+ `metadata.json`). Requirements traceability lives in
[`requirements.md`](./requirements.md); design in [`design.md`](./design.md).

## Status Key

- `[ ]` — pending
- `[~]` — in progress
- `[x]` — complete / evidence-backed
- `[!]` — blocked

---

## [x] Track: Maintenance hardening
Track ID: `maintenance_hardening_20260713`
Goal: Keep documentation, operational state, dependency resolution, and quality
gates trustworthy as the archive grows.
Link: [./tracks/maintenance_hardening_20260713/](./tracks/maintenance_hardening_20260713/)

## [x] Track: Targeted mirror verification
Track ID: `targeted_mirror_verification_20260713`
Goal: Ensure a targeted mirror retry is evaluated independently of stale
verification evidence for other mirrors while retaining the aggregate audit
report.
Link: [./tracks/targeted_mirror_verification_20260713/](./tracks/targeted_mirror_verification_20260713/)

## [x] Track: Operational evidence refresh
Track ID: `operational_evidence_refresh_20260713`
Goal: Align maturity and improvement documentation with the latest verified
mirror, health-monitor, release, and security-gate evidence.
Link: [./tracks/operational_evidence_refresh_20260713/](./tracks/operational_evidence_refresh_20260713/)

## Dependency legend

- `fyi-cli: <track>` — a capability track in the companion `fyi-cli` repo that must
  land before this track's orchestration can function.

## [ ] Track: FOI-O derived re-extraction publication
Track ID: `foio_derived_reextraction_20260714`
Goal: Publish ontology-pinned candidate annotations as a separately versioned
derived layer while preserving immutable archive records.
Depends on: `foi-o` V2 extraction contract and `nlp-policy-nz` FOI-O adapter.
Link: [./tracks/foio_derived_reextraction_20260714/](./tracks/foio_derived_reextraction_20260714/)

## [~] Track: Maximal quality profile
Track ID: `maximal_quality_profile_20260714`
Link: [./tracks/maximal_quality_profile_20260714/](./tracks/maximal_quality_profile_20260714/)

## [ ] Track: Australian FOI corpus readiness
Track ID: `au_foi_corpus_readiness_20260714`
Goal: Produce pinned, rights-aware, jurisdiction-stratified public examples for
FOI-O validation, beginning with Commonwealth and NSW.
Depends on: existing AU multi-instance, rollout, and publication tracks.
Link: [./tracks/au_foi_corpus_readiness_20260714/](./tracks/au_foi_corpus_readiness_20260714/)

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

---

## Multi-jurisdiction expansion tracks

### [x] Track: Multi-instance orchestration
Track ID: `multi_instance_orchestration_20260709` — satisfies **R-40, R-41, R-42**
Goal: Instance registry; CLI `--instance` / env; plumb `--base-url` into seed/sync; multi-source manifests; NZ default regression.
Link: [./tracks/multi_instance_orchestration_20260709/](./tracks/multi_instance_orchestration_20260709/)

### [x] Track: AU RTK ethics and metadata
Track ID: `au_rtk_ethics_metadata_20260709` — satisfies **R-43**
Goal: Policy-research purpose (not AI training); AU ethics/copyright notes; Content-Signal/robots documentation.
Depends on: `multi_instance_orchestration_20260709`.
Link: [./tracks/au_rtk_ethics_metadata_20260709/](./tracks/au_rtk_ethics_metadata_20260709/)

### [x] Track: AU jurisdiction taxonomy
Track ID: `au_jurisdiction_taxonomy_20260709` — satisfies **R-44**
Goal: Body-tag → jurisdiction map; fixtures; authorities with jurisdiction field.
Depends on: `multi_instance_orchestration_20260709`; fyi-cli body enumeration companion.
Link: [./tracks/au_jurisdiction_taxonomy_20260709/](./tracks/au_jurisdiction_taxonomy_20260709/)

### [x] Track: AU NSW historical seed
Track ID: `au_nsw_historical_seed_20260709` — satisfies **R-44, R-21, R-42**
Goal: NSW-only discover→seed→manifest→capped smoke; isolated paths; rate-limited workflows.
Depends on: multi-instance, taxonomy, ethics; fyi-cli live AU smoke.
Link: [./tracks/au_nsw_historical_seed_20260709/](./tracks/au_nsw_historical_seed_20260709/)

### [x] Track: AU jurisdiction rollout controller
Track ID: `au_jurisdiction_rollout_controller_20260709` — satisfies **R-45, R-42**
Goal: Sequential VIC…OTHER after NSW; shared AU limiter; national AU manifest merge.
Depends on: `au_nsw_historical_seed_20260709`.
Link: [./tracks/au_jurisdiction_rollout_controller_20260709/](./tracks/au_jurisdiction_rollout_controller_20260709/)

### [x] Track: Multi-instance publish
Track ID: `multi_instance_publish_20260709` — satisfies **R-46, R-22**
Goal: Separate HF/Zenodo/OSF identity for `au-rtk`; draft-first; never mix into NZ dataset.
Depends on: multi-instance + NSW seed.
Link: [./tracks/multi_instance_publish_20260709/](./tracks/multi_instance_publish_20260709/)

### [x] Track: Multi-instance observability
Track ID: `multi_instance_observability_20260709` — satisfies **R-48**
Goal: Doctor/coverage/horizon per instance and jurisdiction.
Depends on: multi-instance + multi-instance publish.
Link: [./tracks/multi_instance_observability_20260709/](./tracks/multi_instance_observability_20260709/)

### [x] Track: GitHub project multi-jurisdiction issues
Track ID: `github_project_multi_jurisdiction_20260709` — satisfies **R-47**
Goal: Parent/sub-issues for expansion tracks; labels; project + RIOPA sync.
Link: [./tracks/github_project_multi_jurisdiction_20260709/](./tracks/github_project_multi_jurisdiction_20260709/)

### [x] Track: English Alaveteli archive template
Track ID: `english_alaveteli_archive_template_20260709` — satisfies **R-49**
Goal: Post-AU onboarding template; first candidate `uk-wdtk`.
Depends on: AU rollout controller healthy.
Link: [./tracks/english_alaveteli_archive_template_20260709/](./tracks/english_alaveteli_archive_template_20260709/)

### [x] Track: Global Alaveteli archive template
Track ID: `global_alaveteli_archive_template_20260709` — satisfies **R-50**
Goal: Non-English Alaveteli onboarding template; locale/GDPR notes.
Depends on: English template track.
Link: [./tracks/global_alaveteli_archive_template_20260709/](./tracks/global_alaveteli_archive_template_20260709/)

### [x] Track: Historical source import
Track ID: `historical_source_import_20260711`
Goal: Import downloaded Morph and Internet Archive index exports offline with checksums, provenance, and URL-level deduplication.
Link: [./tracks/historical_source_import_20260711/](./tracks/historical_source_import_20260711/)

### [x] Track: Working Alaveteli sites
Track ID: `working_alaveteli_sites_20260711`
Goal: Add four verified authority-catalog exports to a sequential, overnight,
explicitly confirmed archive workflow.
Link: [./tracks/working_alaveteli_sites_20260711/](./tracks/working_alaveteli_sites_20260711/)

### [x] Track: Alaveteli source modes
Track ID: `alaveteli_source_modes_20260712`
Goal: Expand coverage through fyi-cli feeds, offline exports, Internet Archive
indexes, and future official datasets without increasing origin-site load.
Link: [./tracks/alaveteli_source_modes_20260712/](./tracks/alaveteli_source_modes_20260712/)

### [x] Track: Coverage progress observability
Track ID: `coverage_progress_observability_20260713`
Goal: Make the deliberately slow historical backfill measurable in health reports
without increasing source traffic or changing its off-peak schedule.
Link: [./tracks/coverage_progress_observability_20260713/](./tracks/coverage_progress_observability_20260713/)

### [~] Track: Alaveteli site-wide queue
Track ID: `alaveteli_sitewide_queue_20260713`
Goal: Advance working Alaveteli archives through checkpointed public-feed queues
and verified capture state.
Link: [./tracks/alaveteli_sitewide_queue_20260713/](./tracks/alaveteli_sitewide_queue_20260713/)

---

## Companion capability tracks (in fyi-cli)

### [ ] Track: Full-corpus process projection and continuation
Track ID: `full_corpus_process_projection_20260721`
Goal: Build and maintain revisioned public-safe case/event projections for full-corpus process mining.
Link: [./tracks/full_corpus_process_projection_20260721/](./tracks/full_corpus_process_projection_20260721/)
GitHub: [#196](https://github.com/edithatogo/fyi-archive/issues/196), registered as a subissue of [foi-process #36](https://github.com/edithatogo/foi-process/issues/36).
Upstream: [fyi-cli #231](https://github.com/edithatogo/fyi-cli/issues/231) / `process-event-export_20260721`.
Downstream: [foi-process #37](https://github.com/edithatogo/foi-process/issues/37) / `T10-full-corpus-process-mining`.

---

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

## Archived tracks

### [x] Track: GitHub project best practices and workflow maximization
Track ID: `github_project_best_practices_20260701`
Goal: Maximize GitHub Projects v2 best practices, native workflows, views, and GraphQL automation while keeping custom code limited to cross-project sync.
Link: [./archive/github_project_best_practices_20260701/](./archive/github_project_best_practices_20260701/)

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
