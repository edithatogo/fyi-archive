# Plan: security_supply_chain_20260627

## Phase 1: SBOM + provenance
- [x] 1.1 `scripts/gen_sbom.py` (cyclonedx) → `dist/sbom.cdx.json`.
- [x] 1.2 `provenance.json` generation (commit, lockfile hash, fetch window, WACZ hashes).
- [x] 1.3 `actions/attest-build-provenance@v4` wired into publish/release.

## Phase 2: Continuous security
- [x] 2.1 CodeQL + Scorecard workflows (SARIF upload).
- [x] 2.2 Secret-presence validation workflows (HF/Zenodo/OSF).
- [x] 2.3 `make security-audit` (pip-audit).

## Phase 3: Optional signing
- [x] 3.1 Document Sigstore/cosign keyless opt-in (off by default).
- [x] 3.2 Leave an improvement-backlog entry to enable once reviewed.
