# Maturity Checklist

Tracks the project's climb from pre-alpha to a SOTA, evidence-backed archive.

## Phase 0 — Bootstrap (this repo's `repo_bootstrap`)
- [x] Standalone git repo + remote
- [x] `pyproject.toml` (uv, ruff, ty), `VERSION`, `.python-version`
- [x] Conductor setup (product/tech-stack/workflow/tracks)
- [x] Quality tooling (pre-commit, markdownlint, vale, taplo, typos, zizmor, actionlint, Renovate)
- [x] README + NOTICE + SECURITY + CITATION + DATASET_CARD + .zenodo.json
- [ ] First commit pushed; workspace submodule wired

## Phase 1 — Storage only (read-only)
- [ ] `fyi-cli` capture tracks delivered (enumeration, capture, diff, health)
- [ ] Historical-seed orchestration; capped smoke seed validated end-to-end
- [ ] Daily prospective sync with HF hash-verify
- [ ] HF live dataset populated
- [ ] Zenodo annual DOI snapshot (draft-first, gated)
- [ ] OSF project + components mirror
- [ ] Croissant + Frictionless metadata emitted + validated
- [ ] DuckDB read-only export + CycloneDX SBOM + provenance
- [x] release-please dynamic versioning/releases

## Phase 2 — Hardening (future)
- [ ] Coverage ≥ 80%
- [ ] Mirror-parity CI gate
- [ ] Full-site crawl complete and reconciled
- [ ] Annual provenance review
