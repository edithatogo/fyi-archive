# Plan: versioning_releases_20260627

## Phase 1: release-please
- [x] 1.1 `release.yml` configured for a Python app (`pyproject.toml` +
       `VERSION` + `src/fyi_archive/version.py` as version files).
- [x] 1.2 `CHANGELOG.md` bootstrapped; release-please owns it thereafter.
- [ ] 1.3 CONTRIBUTING note on Conventional Commits.

## Phase 2: Version-consistency gate
- [x] 2.1 `check_version_consistency.py` as a required `tests.yml` gate.
- [ ] 2.2 release-please bump propagates to all three sources.

## Phase 3: Release artifacts + Zenodo link
- [ ] 3.1 Release job attaches `dist/` bundle + SBOM + provenance.
- [ ] 3.2 `CITATION.cff` DOI update step wired into `zenodo_publish.yml`.
- [ ] 3.3 Independent versioning axes documented.
