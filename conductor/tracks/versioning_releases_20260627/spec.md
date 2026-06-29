# Track: Versioning & releases
Track ID: `versioning_releases_20260627`
Satisfies: **R-16** (dynamic versioning and releases using GitHub Actions).

## Goal

Automated, dynamic SemVer versioning and releases driven entirely by GitHub Actions,
layered onto the family's SemVer + manifest-hash provenance model.

## Scope

- **release-please** (`release-please.yml`): consumes Conventional Commits on `main`,
  opens a release PR with the version bump + generated `CHANGELOG.md`, and cuts a
  GitHub Release (`vX.Y.Z`) when merged.
- Version sources kept in sync: `pyproject.toml` `[project].version` == `VERSION` ==
  `src/fyi_archive/version.__version__`, enforced by
  `scripts/check_version_consistency.py` as a CI gate.
- `CHANGELOG.md` generated/managed by release-please.
- Release attaches the `dist/` bundle (WACZ, DuckDB, manifest, `.SHA256SUMS`,
  `provenance.json`, `sbom.cdx.json`) — produced by `publish_archives`/release job.
- **Annual Zenodo DOI snapshot** (manual `zenodo_publish.yml`) as the archival release
  (family convention); `CITATION.cff` updated with the DOI.
- Independent versioning axes documented: package (SemVer), dataset version, schema
  version, HF revision, Zenodo DOI — intentionally independent.

## Out of scope

- The publish adapters themselves (`multi_mirror_publish`).
- SBOM/provenance generation (`security_supply_chain`).

## Acceptance criteria

- [x] A `feat:` commit on `main` causes release-please to open a release PR bumping
      the version and updating `CHANGELOG.md`.
- [x] Merging the release PR cuts a tagged GitHub Release with the `dist/` artifacts.
- [x] `check_version_consistency.py` fails CI on any source drift.
- [x] `CITATION.cff` carries the latest Zenodo DOI after an annual publish.
- [x] Versioning axes documented in `tech-stack.md`.

## Risks

- release-please config drift → pin the action; review config on major bumps.
- Accidental non-conventional commits → CONTRIBUTING docs enforce the format.
