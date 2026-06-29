# Track: Security & supply chain
Track ID: `security_supply_chain_20260627`
Satisfies: **R-18** (checks), **R-24** (SBOM + provenance). Provides: **R-26** (optional Sigstore).

## Goal

Make every release evidence-backed and the project's supply chain continuously
audited: SBOM, build-provenance attestations, static analysis, and secret hygiene.

## Scope

- CycloneDX SBOM (`cyclonedx-bom`) generated per release into `dist/sbom.cdx.json`,
  attached to the GitHub Release and included in the Zenodo deposition.
- `actions/attest-build-provenance@v4` on release artifacts (WACZ, DuckDB, manifest,
  `.SHA256SUMS`, `provenance.json`).
- `provenance.json` (source commit, fetch window, `uv.lock` hash, runner env, WACZ
  hashes) pinned in the release + Zenodo metadata.
- CodeQL + OpenSSF Scorecard (continuous; SARIF uploaded).
- Secret-presence validation workflows (HF/Zenodo/OSF tokens) — model on
  `sm-govt-nz`'s `validate_*.yml`.
- `pip-audit` (`make security-audit`) over the installed env.
- Optional (off by default, documented opt-in): keyless Sigstore/cosign signing of
  release artifacts.

## Out of scope

- Release *cutting* mechanics (`versioning_releases`).
- Publishing to mirrors (`multi_mirror_publish`).

## Acceptance criteria
- [x] A release produces `sbom.cdx.json` + `provenance.json` + build-provenance
       attestation.
- [x] CodeQL + Scorecard run continuously; results uploaded.
- [x] Secret-presence checks fail CI clearly when a required token is missing.
- [x] `make security-audit` runs `pip-audit` without blocking errors.
- [x] Sigstore opt-in documented (disabled by default).

## Risks

- Attestation tooling churn → pin action versions; Renovate maintains them.
