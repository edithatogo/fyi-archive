# Plan: multi_mirror_publish_20260627

## Phase 1: HF adapter (live)

- [x] 1.1 `hf_publish.py`: `upload_large_folder` + hf-xet; repo-id from `HF_REPO_ID`.
- [x] 1.2 Restore + verify helpers (snapshot_download + SHA-256).
- [x] 1.3 Tests with mocked HF API (respx).

## Phase 2: Zenodo adapter (annual, gated)

- [x] 2.1 `zenodo_publish.py`: draft-first deposition via raw `requests`; sandbox +
       production endpoints.
- [x] 2.2 `zenodo_publish.yml` protected environment + confirm string.
- [x] 2.3 Tests for draft creation + publish-gating.

## Phase 3: OSF adapter (project + components)

- [x] 3.1 `osf_publish.py`: OSF API v2 — create project + components (HF, Zenodo).
- [x] 3.2 File upload (≤5 GB per OSF storage rules); idempotent component creation.
- [x] 3.3 Tests with mocked OSF API.

## Phase 4: Metadata + export + SBOM

- [x] 4.1 `metadata.py`: Croissant (JSON-LD), Frictionless, schema.org → `metadata/`.
- [x] 4.2 `export.py`: Parquet-backed DuckDB read-only export → `dist/fyi_archive.duckdb`.
- [x] 4.3 `scripts/gen_sbom.py` (CycloneDX) → `dist/sbom.cdx.json`.
- [x] 4.4 `validate_metadata.yml`: schema validation + parity cross-check.

## Phase 5: Release machinery

- [x] 5.1 `publish_archives.yml` (build dist + attest provenance + multi-target).
- [x] 5.2 `release.yml` (release-please SemVer + changelog + GitHub Release).
- [x] 5.3 Attach WACZ + DuckDB + SBOM + provenance to the release.
- [x] 5.4 Monthly scheduled Hugging Face publish refresh; Zenodo/OSF remain
      manual/gated targets.

## Phase 6: Mirror verification evidence

- [x] 6.1 Local artifact inventory: filename, byte size, SHA-256 digest.
- [x] 6.2 HF verification: remote manifest re-download + SHA-256 evidence.
- [x] 6.3 Zenodo verification: deposition file listing compared to local artifacts.
- [x] 6.4 OSF verification: component file listing compared to local artifacts.
- [x] 6.5 `publish_archives.yml` writes `dist/mirror_verification.json` and fails on
      failed mirror artifact comparison.

## Dependencies

- Builds on the manifest produced by `historical_seed_orchestration`.
- Independent of `fyi-cli`'s internal tracks (consumes outputs only).
- Live mirror population is evidence-backed by GHA run 28378172250 at 3d9296c:
  HF remote manifest SHA-256 verified, Zenodo draft artifacts verified, OSF
  mirror artifacts verified, publish evidence uploaded, and provenance attested.
