# Track: Multi-mirror publish
Track ID: `multi_mirror_publish_20260627`

## Goal

Wire all three distribution mirrors — **Hugging Face** (live, content-revised),
**Zenodo** (annual DOI snapshot, draft-first, gated), **OSF** (project + components
mirror) — plus dataset metadata, the DuckDB read-only export, SBOM, build provenance,
and `release-please` dynamic versioning/releases.

## Scope

- `publish_archives.yml`: weekly cron + `workflow_dispatch` with
  `publication_target ∈ {huggingface, zenodo, osf, all, all_with_osf}` and a `publish`
  gate. Builds `dist/` (tar.gz, `.manifest.json`, `.SHA256SUMS`, `.release-evidence.json`,
  `fyi_archive.duckdb`, `*.wacz`, `provenance.json`, `sbom.cdx.json`); runs
  `actions/attest-build-provenance@v4`. Each attempted mirror writes a normalized
  `dist/mirror_verification.json` entry containing record count, required artifact
  filenames, local SHA-256 digests, remote checksums/URLs where exposed, and an
  enforced pass/fail comparison.
- Mirror adapters:
  - HF: `upload_large_folder` + hf-xet (live dataset).
  - Zenodo: raw `requests` to the deposition API; **draft-first**; `publish` requires
    the `zenodo-production` protected environment + confirm string `publish-zenodo-doi`.
  - OSF: OSF API v2 — create project + one component per mirror (HF, Zenodo); upload
    files (≤5 GB per OSF storage rules).
- `zenodo_publish.yml`: the gated production publish workflow.
- **Per-item licence propagation (R-31):** the `license` + `attribution` fields
  captured per record (see fyi-cli `faithful-archive-capture`) are carried through to
  the HF dataset, the DuckDB export, and the Croissant/Frictionless metadata; mirror
  artifacts never assert a licence broader than the source declared. Code (MIT) and
  data (source rights) licences are kept separate in every channel.
- Metadata: `metadata/{croissant.jsonld, frictionless.json, schema.org.jsonld}`;
  `validate_metadata.yml` CI checks schemas + cross-checks counts (HF/Zenodo/OSF parity).
- DuckDB read-only export (`export.py`): Parquet-backed `dist/fyi_archive.duckdb`.
- `release-please.yml`: conventional-commits → SemVer bump + `CHANGELOG.md` + GitHub
  Release (the dynamic versioning/releases via GHA).
- SBOM: `scripts/gen_sbom.py` (CycloneDX) attached to each release + Zenodo deposition.

## Out of scope

- Changing capture/diff behaviour (that's `fyi-cli`).
- Search index / serving API (phase 1 non-goal).

## Acceptance criteria

- [~] `publish_archives.yml` builds `dist/` and attests provenance; `publication_target=huggingface`
       uploads successfully and the HF dataset is loadable.
- [~] Zenodo draft creation succeeds in sandbox; production publish is blocked unless
       run in `zenodo-production` with the confirm string.
- [~] OSF project + components created; a sample file uploaded and listed.
- [~] Croissant + Frictionless validate; HF auto-detects Croissant.
- [x] `release.yml` cuts a `v0.1.0`-class release from a `feat:` commit with a
       generated changelog.
- [x] SBOM generated and attached to a release.
- [x] Publish jobs produce machine-readable mirror verification evidence and fail when
      required artifacts are missing or known remote checksums/sizes disagree.

## Risks

- Token scope mistakes (HF write, Zenodo publish, OSF project-create) → documented in
  `docs/` + `validate_*` secret-presence checks in CI.
- Zenodo/OSF metadata drift → metadata workflow fails loudly, not silently.
