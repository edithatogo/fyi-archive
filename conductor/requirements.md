# Requirements (MoSCoW)

Derived from [`initial-concept.md`](./initial-concept.md) (the verbatim user brief).
Each requirement has a stable ID (`R-xx`), a MoSCoW priority, the source clause it
traces to, and the track(s) that satisfy it. Priorities:

- **M** — Must have (the archive is not fit for purpose without it)
- **S** — Should have (important; deliver in phase 1 if feasible)
- **C** — Could have (desirable; phase 2 candidate)
- **W** — Won't have (this phase) — explicitly excluded to prevent scope creep

---

## 1. Scope & source

| ID | Priority | Requirement | Source clause | Track(s) |
| --- | --- | --- | --- | --- |
| R-01 | **M** | Archive the **entire public surface** of `https://fyi.org.nz/` (every OIA request, its metadata, page, and attachments). | "archives this entire site: https://fyi.org.nz/" | `bulk-site-enumeration` (fyi-cli), `faithful-archive-capture` (fyi-cli), `historical_seed_orchestration` |
| R-02 | **M** | Capture is **read-only**: no login, no write/submit, no auth for reads. | "just storing it, read only" | `faithful-archive-capture` (fyi-cli), `docs/ethics-and-compliance` |
| R-03 | **M** | Initial phase is **storage only** — no analysis, OCR, or normalisation. | "we won't be analysing it at all, just storing it" | (non-goal enforced across all tracks) |
| R-04 | **W** | Analysis / OCR / normalisation / search index / serving API. | implied exclusion | future tracks (not phase 1) |

## 2. Capture tooling

| ID | Priority | Requirement | Source clause | Track(s) |
| --- | --- | --- | --- | --- |
| R-05 | **M** | Use the user's tool **`fyi-cli`** (https://github.com/edithatogo/fyi-cli) as the capture engine, **adding features to it where necessary** rather than reimplementing capture elsewhere. | "use this tool I created … fyi-cli" + "improving and adding features if necessary" | `bulk-site-enumeration`, `faithful-archive-capture`, `archival-content-diff`, `archive-health-doctor` (all in fyi-cli) |
| R-06 | **M** | `fyi-archive` is a **thin orchestration + distribution** consumer of `fyi-cli`; it contains no network-fetching logic. | user direction during execution | all `fyi-archive` orchestration tracks |

## 3. Repositories & mirrors

| ID | Priority | Requirement | Source clause | Track(s) |
| --- | --- | --- | --- | --- |
| R-07 | **M** | Use the git repo **`https://github.com/edithatogo/fyi-archive`** as the project home. | "use this git repo … fyi-archive" | `repo_bootstrap` |
| R-08 | **M** | Mirror a copy to **Hugging Face** (`https://huggingface.co/edithatogo`). | "create a copy in my hugging face" | `multi_mirror_publish`, `prospective_sync_orchestration` |
| R-09 | **M** | Set up an archive on **Zenodo**. | "setup an archive for zenodo" | `multi_mirror_publish` |
| R-10 | **M** | Set up an archive on **OSF**. | "setup an archive for … osf" | `multi_mirror_publish` |
| R-11 | **M** | Follow the **conventions of the user's other archives**: `hathi-nz`, `sm-govt-nz`, `corpus-legislation-nz`, `corpus-nz-hansard`, `corpus-cases-medilegal-nz`. | "follow the conventions of other archives" | `repo_bootstrap` (scaffold cloned from family) |
| R-12 | **M** | Wire `fyi-archive` as a **submodule** in the `legal-nz` workspace, like the siblings. | user direction / sibling pattern | `repo_bootstrap` |

## 4. Phasing

| ID | Priority | Requirement | Source clause | Track(s) |
| --- | --- | --- | --- | --- |
| R-13 | **M** | **Start with historical storage** (full backfill of existing corpus) before prospective archiving. | "start by initiating the historical storage" | `historical_seed_orchestration` (+ fyi-cli capture tracks) |
| R-14 | **M** | Then set up **prospective archiving** (ongoing capture of new/changed requests). | "then by setting up the prospective archiving" | `prospective_sync_orchestration` (+ fyi-cli `archival-content-diff`) |

## 5. Automation, versioning, quality

| ID | Priority | Requirement | Source clause | Track(s) |
| --- | --- | --- | --- | --- |
| R-15 | **M** | **Entirely automated** via CI/CD (no manual steps for ongoing operation). | "entirely automated" | `ci_cd_foundation`, `historical_seed_orchestration`, `prospective_sync_orchestration`, `multi_mirror_publish` |
| R-16 | **M** | **Dynamic versioning and releases using GitHub Actions.** | "dynamic versioning and releases using the github actions" | `versioning_releases` (`release-please`) |
| R-17 | **M** | Use **bleeding-edge libraries and tools** (current best-in-class). | "bleeding edge libraries, tools" | `tech-stack.md` (httpx, warcio, py-wacz, hf-xet, polars, duckdb, croissant, ruff, ty, zizmor, etc.) |
| R-18 | **M** | **CI/CD, code quality, checks, etc.** (lint, types, tests, coverage, workflow security, supply chain). | "cicd, code quality, checks, etc." | `ci_cd_foundation`, `code_quality_gates`, `security_supply_chain` |
| R-19 | **M** | Follow family conventions for data/manifest/provenance model (manifest-hash release evidence, HF revision tracking, Zenodo DOI snapshots, protected publication). | "conventions of other archives" | `multi_mirror_publish`, `observability_quality` |

## 6. Reliability & safety (derived — Must)

| ID | Priority | Requirement | Source clause | Track(s) |
| --- | --- | --- | --- | --- |
| R-20 | **M** | Capture is **polite & safe** (rate-limited, robots-aware, contactable UA, hard run caps) since the source is a real third-party service. | implied by read-only + automation | `bulk-site-enumeration` (fyi-cli), `docs/ethics-and-compliance` |
| R-21 | **M** | Historical backfill is **resumable** (survives interrupts) and **bounded** (never one monolithic overrunning job). | implied by "entire" + automation | `historical_seed_orchestration` |
| R-22 | **M** | Publishing is **draft-first**; production Zenodo DOI publish is gated behind a protected environment. | family convention + safety | `multi_mirror_publish` |
| R-23 | **S** | **Mirror parity** is observable and CI-gated (HF vs Zenodo vs OSF record counts). | implied by multi-mirror | `observability_quality` |
| R-24 | **S** | Releases carry **SBOM + build provenance** (SLSA-style attestations). | bleeding-edge + checks | `security_supply_chain`, `versioning_releases` |
| R-25 | **S** | Dataset metadata in **Croissant + Frictionless** for ML/FAIR discoverability. | bleeding-edge + conventions | `multi_mirror_publish` |

## 6a. Copyright & licensing provisions (user-specified)

| ID | Priority | Requirement | Source clause | Track(s) |
| --- | --- | --- | --- | --- |
| R-30 | **M** | **Document the NZ copyright provisions** under which preservation/redistribution is permitted, with citations: Copyright Act 1994 (Crown copyright s.26 / no-copyright-in-certain-works s.27 / interpretation s.2; 100-year Crown term), the **NZGOAL** open-licensing framework (CC BY 4.0 / "no known rights"), and **IPONZ** copyright guidance. | user-supplied URLs (OECD/NZGOAL, legislation.govt.nz Copyright Act 1994, iponz.govt.nz) | `repo_bootstrap` (docs/copyright-and-licensing.md) |
| R-31 | **M** | **Record per-item licence + attribution** (source-declared, verbatim) in the manifest for every captured record; assert **no new rights** over archived data; keep **code (MIT) vs data (source rights)** licences separate. | derived from R-30 + faithful capture | `faithful-archive-capture` (fyi-cli), `historical_seed_orchestration`, `multi_mirror_publish` |
| R-32 | **M** | Provide a **takedown** contact/process for rights holders. | good-faith obligation on a public archive | `repo_bootstrap` (docs), `multi_mirror_publish` |

## 7. Could / Won't (this phase)

| ID | Priority | Requirement | Track(s) |
| --- | --- | --- | --- |
| R-26 | **C** | Keyless Sigstore/cosign signing of release artifacts (opt-in). | `security_supply_chain` (opt-in) |
| R-27 | **C** | Coverage ramp to ≥80%. | `observability_quality` |
| R-28 | **W** | Full-text search index / query API over the archive. | future |
| R-29 | **W** | OCR / text extraction / entity normalisation. | future |

## 8. Multi-jurisdiction expansion

Generalises the NZ phase-1 contract to **per-instance** Alaveteli surfaces. Capture
remains exclusively in `fyi-cli` (R-05, R-06). Purpose is **public-policy research and
operational transparency**, not AI training.

| ID | Priority | Requirement | Source clause | Track(s) |
| --- | --- | --- | --- | --- |
| R-40 | **M** | Instance-aware orchestration: seed/sync/manifest/publish accept `instance_id` (default `nz-fyi`); no NZ regression. | multi-jurisdiction plan | `multi_instance_orchestration_20260709` |
| R-41 | **M** | Capture remains exclusively in **fyi-cli**; archive only invokes CLI with `--base-url` / instance config and never reimplements fetch/WARC. | two-repo discipline | all multi-jurisdiction tracks |
| R-42 | **M** | Respect **robots.txt**, shared **rate limits**, and contactable UA; per-instance limiter namespaces; never exceed fyi-cli site-safe defaults without documented justification. | politeness + RTK ops | `multi_instance_orchestration_20260709`, fyi-cli rate limiter |
| R-43 | **M** | Archive purpose is **public-policy research / operational transparency**, not AI training; dataset cards and ethics docs state this; honour Content-Signals where present. | product purpose | `au_rtk_ethics_metadata_20260709` |
| R-44 | **M** | AU RTK archive via `au-rtk`, with **jurisdiction taxonomy** from body tags; first production slice **NSW**. | AU RTK integration | `au_jurisdiction_taxonomy_20260709`, `au_nsw_historical_seed_20260709` |
| R-45 | **M** | After NSW is evidence-backed, **automated iteration** through remaining AU jurisdictions in fixed order (VIC→QLD→…→federal→OTHER). | state-by-state rollout | `au_jurisdiction_rollout_controller_20260709` |
| R-46 | **S** | Separate mirror identity per instance (e.g. `edithatogo/rtk-archive-au`); NZ dataset unchanged. | multi-mirror | `multi_instance_publish_20260709` |
| R-47 | **S** | GitHub issues + sub-issues for each track, linked to Projects v2 and mirrored to RIOPA. | GitHub project model | `github_project_multi_jurisdiction_20260709` |
| R-48 | **S** | Doctor/coverage/horizon are instance- and jurisdiction-aware. | observability | `multi_instance_observability_20260709` |
| R-49 | **C** | English Alaveteli fleet archive onboarding template (post-AU). | global ladder | `english_alaveteli_archive_template_20260709` |
| R-50 | **C** | Non-English Alaveteli archive onboarding (post-English). | global ladder | `global_alaveteli_archive_template_20260709` |
| R-51 | **W** | Non-Alaveteli FOI portals; LLM training pipelines; NLP over archives. | explicit non-goal | future |

---

## Requirement → track traceability summary

| Requirement IDs | Primary track(s) |
| --- | --- |
| R-07, R-11, R-12, R-30, R-32 | `repo_bootstrap` |
| R-15, R-18 | `ci_cd_foundation`, `code_quality_gates`, `security_supply_chain` |
| R-16, R-24 | `versioning_releases` |
| R-01, R-02, R-13, R-20, R-21 | `historical_seed_orchestration` + fyi-cli `bulk-site-enumeration`, `faithful-archive-capture` |
| R-14 | `prospective_sync_orchestration` + fyi-cli `archival-content-diff` |
| R-08, R-09, R-10, R-22, R-25, R-31 | `multi_mirror_publish` (+ fyi-cli `faithful-archive-capture` for R-31 capture) |
| R-19, R-23 | `observability_quality` + fyi-cli `archive-health-doctor` |
| R-03, R-04, R-28, R-29, R-51 | (non-goals / explicit exclusions) |
| R-05, R-06, R-41 | (architectural principle — fyi-cli owns capture) |
| R-17 | `tech-stack.md` |
| R-40, R-42 | `multi_instance_orchestration_20260709` |
| R-43 | `au_rtk_ethics_metadata_20260709` |
| R-44 | `au_jurisdiction_taxonomy_20260709`, `au_nsw_historical_seed_20260709` |
| R-45 | `au_jurisdiction_rollout_controller_20260709` |
| R-46 | `multi_instance_publish_20260709` |
| R-47 | `github_project_multi_jurisdiction_20260709` |
| R-48 | `multi_instance_observability_20260709` |
| R-49 | `english_alaveteli_archive_template_20260709` |
| R-50 | `global_alaveteli_archive_template_20260709` |
