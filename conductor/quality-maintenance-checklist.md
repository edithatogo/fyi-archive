# Quality & Maintenance Checklist

## Weekly
- [ ] Review `hf_sync.yml` runs; confirm green + SHA-256 verify passed.
- [ ] Review `conductor/archive_health.json` (freshness, coverage gaps, mirror parity).
- [ ] Triage CI-learning candidates (`ci-learning-candidates.yml`).

## Monthly
- [ ] Review + merge Renovate dependency PRs.
- [ ] Rotate tokens approaching expiry (HF/Zenodo/OSF).
- [ ] `make security-audit` (`pip-audit`); review `scorecard`/`codeql` findings.

## Annually
- [ ] Trigger `zenodo_publish.yml` for the DOI snapshot; update `CITATION.cff`.
- [ ] Review `docs/ethics-and-compliance.md` against any source-site changes.
- [ ] Reconcile full corpus against the live site (gap-fill).
