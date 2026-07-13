# Maturity Checklist

Tracks the project's climb from pre-alpha to a SOTA, evidence-backed archive.

Status refreshed 2026-07-13 against track plans and retained GitHub Actions
evidence. `conductor/archive_health.json` remains a workflow artifact, not a
committed source of truth.

## Phase 0 — Bootstrap (this repo's `repo_bootstrap`)
- [x] Standalone git repo + remote
- [x] `pyproject.toml` (uv, ruff, ty), `VERSION`, `.python-version`
- [x] Conductor setup (product/tech-stack/workflow/tracks)
- [x] Quality tooling (pre-commit, markdownlint, vale, taplo, typos, zizmor, actionlint, Renovate)
- [x] README + NOTICE + SECURITY + CITATION + DATASET_CARD + .zenodo.json
- [x] First commit pushed; workspace submodule wired

## Phase 1 — Storage only (read-only)
- [x] `fyi-cli` capture tracks delivered (enumeration, capture, diff, health)
- [x] Historical-seed orchestration; capped smoke seed validated end-to-end
      (GHA 28378172250; `conductor/live_seed_smoke.json`)
- [x] Daily prospective sync with HF hash-verify
      (GHA 28378940339 empty-diff proof; `hf_sync.yml`)
- [x] HF live dataset populated (smoke corpus; full-site growth ongoing)
- [x] Zenodo annual DOI snapshot (draft-first, gated; draft path verified on smoke)
- [x] OSF project + components mirror (9 artifacts verified in GHA run
      29245786272)
- [x] Croissant + Frictionless metadata emitted + validated
- [x] DuckDB read-only export + CycloneDX SBOM + provenance
- [x] release-please dynamic versioning/releases

### Phase 1 operational follow-through (not track blockers)
- [~] Grow corpus beyond smoke seed toward coverage target (60% in `archive_health.json`); health output now reports target records, remaining records, and whether the target is met. Remaining work is the deliberately slow historical backfill.
- [x] Keep the workflow-produced archive-health evidence fresh after each
      successful sync/publish (latest successful monitor: GHA 29250400404;
      healthy parity and coverage evidence uploaded).
- [x] Production Zenodo DOI publish completed through the protected environment after explicit confirmation: `10.5281/zenodo.21338285` (record `21338285`).

## Phase 2 — Hardening (future)
- [ ] Coverage ≥ 80%
- [ ] Mirror-parity CI gate
- [ ] Full-site crawl complete and reconciled
- [ ] Annual provenance review
- [ ] Optional Sigstore/cosign keyless signing (see `improvement-backlog.md`)
