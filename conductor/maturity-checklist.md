# Maturity Checklist

Tracks the project's climb from pre-alpha to a SOTA, evidence-backed archive.

Status refreshed 2026-07-09 against track plans, GHA smoke evidence, and
`conductor/archive_health.json`.

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
- [x] OSF project + components mirror (artifact path verified on smoke)
- [x] Croissant + Frictionless metadata emitted + validated
- [x] DuckDB read-only export + CycloneDX SBOM + provenance
- [x] release-please dynamic versioning/releases

### Phase 1 operational follow-through (not track blockers)
- [ ] Grow corpus beyond smoke seed toward coverage target (60% in `archive_health.json`)
- [ ] Keep committed `conductor/archive_health.json` fresh after each successful sync/publish
- [ ] Production Zenodo DOI publish (explicit confirmation string + protected environment)

## Phase 2 — Hardening (future)
- [ ] Coverage ≥ 80%
- [ ] Mirror-parity CI gate
- [ ] Full-site crawl complete and reconciled
- [ ] Annual provenance review
- [ ] Optional Sigstore/cosign keyless signing (see `improvement-backlog.md`)
