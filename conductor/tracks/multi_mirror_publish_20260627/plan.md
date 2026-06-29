# Plan: multi_mirror_publish_20260627

## Phase 1: HF adapter (live)

- [ ] 1.1 `hf_publish.py`: `upload_large_folder` + hf-xet; repo-id from `HF_REPO_ID`.
- [ ] 1.2 Restore + verify helpers (snapshot_download + SHA-256).
- [ ] 1.3 Tests with mocked HF API (respx).

## Phase 2: Zenodo adapter (annual, gated)

- [ ] 2.1 `zenodo_publish.py`: draft-first deposition via raw `requests`; sandbox +
       production endpoints.
- [ ] 2.2 `zenodo_publish.yml` protected environment + confirm string.
- [ ] 2.3 Tests for draft creation + publish-gating.

## Phase 3: OSF adapter (project + components)

- [ ] 3.1 `osf_publish.py`: OSF API v2 — create project + components (HF, Zenodo).
- [ ] 3.2 File upload (≤5 GB per OSF storage rules); idempotent component creation.
- [ ] 3.3 Tests with mocked OSF API.

## Phase 4: Metadata + export + SBOM

- [ ] 4.1 `metadata.py`: Croissant (JSON-LD), Frictionless, schema.org → `metadata/`.
- [ ] 4.2 `export.py`: Parquet-backed DuckDB read-only export → `dist/fyi_archive.duckdb`.
- [ ] 4.3 `scripts/gen_sbom.py` (CycloneDX) → `dist/sbom.cdx.json`.
- [~] 4.4 `validate_metadata.yml`: schema validation + parity cross-check.

## Phase 5: Release machinery

- [ ] 5.1 `publish_archives.yml` (build dist + attest provenance + multi-target).
- [~] 5.2 `release.yml` (release-please SemVer + changelog + GitHub Release).
- [ ] 5.3 Attach WACZ + DuckDB + SBOM + provenance to the release.

## Dependencies

- Builds on the manifest produced by `historical_seed_orchestration`.
- Independent of `fyi-cli`'s internal tracks (consumes outputs only).
