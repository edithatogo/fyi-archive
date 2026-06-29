# Technology Stack

This repo is the **orchestration + distribution** layer. Capture tooling lives in
`fyi-cli`; this stack covers only what `fyi-archive` needs to drive it and publish.

## Runtime

- **Language:** Python ≥ 3.12 (tested on 3.12 and 3.14).
- **Environment / package manager:** `uv` (Rust-backed), with a committed `uv.lock`
  installed via `uv sync --extra dev --frozen`.

## Core libraries

- **CLI:** `typer` + `rich` (family consistency with `corpus-law-nz` /
  `corpus-cases-medilegal-nz`).
- **Config:** `pydantic` + `pydantic-settings` (v2).
- **Logging:** `loguru` (family standard; `[tool.legal_nz] logging = "loguru"`).
- **Data:** `polars` + `pyarrow` (columnar manifests/Parquet); **DuckDB** read-only
  analytics export.
- **Shelling out to the capture tool:** the `fyi-cli` package as a pinned local path
  dependency.

## Publishing / mirrors

- **Hugging Face:** `huggingface_hub` with `hf-xet` (content-addressable dedup);
  `upload_large_folder` (resumable) for the live dataset.
- **Zenodo:** raw `requests` to the deposition API; draft-first.
- **OSF:** raw `requests` to OSF API v2 (project + components + file upload).

## Dataset metadata

- **Croissant** (MLCommons, JSON-LD) — primary ML metadata; `mlcroissant` loader checks.
- **Frictionless Data** (`frictionless`) for the tabular manifest layer.
- **schema.org / DATASET** JSON-LD for Zenodo/HF discovery.

## Development tools

- **Lint/format:** `ruff` (ruleset mirrors `corpus-cases-medilegal-nz`).
- **Type check:** `ty` (Astral; the family's direction, replacing mypy/pyright).
- **Tests:** `pytest` + `pytest-cov` (`fail_under = 60`, ramping), `pytest-asyncio`,
  `hypothesis`, `respx` (HTTP mocking).
- **Workflow lint:** `actionlint`; **workflow security:** `zizmor`.
- **TOML:** `taplo`; **spelling:** `typos`; **markdown:** `markdownlint-cli`;
  **prose:** `vale`.
- **Dead code / deps:** `vulture`, `deptry`.
- **Hooks:** `pre-commit` (ruff).
- **Dependency updates:** Renovate.

## Security & supply chain

- `codeql` + OpenSSF `scorecard`.
- CycloneDX SBOM per release (`cyclonedx-bom`).
- `actions/attest-build-provenance@v4` on release artifacts.
- `release-please` for automated SemVer + changelog + GitHub Releases.

## Versioning Axes

The project tracks several independent versions:

- **Package SemVer:** `pyproject.toml`, `VERSION`, and
  `src/fyi_archive/version.py`; updated by release-please and enforced by
  `scripts/check_version_consistency.py`.
- **Dataset publication version:** the version of a published archive bundle or
  mirror snapshot; it may change when data changes even if package code does not.
- **Schema version:** manifest and changes schema evolution; this is independent of
  package SemVer until schema tooling is implemented.
- **Hugging Face revision:** content-addressed dataset repository revision for the
  live mirror.
- **Zenodo DOI:** immutable annual snapshot identifier, updated in `CITATION.cff`
  after the protected Zenodo publish workflow succeeds.

## Project structure

See `docs/README.md` (architecture) and the repository `README.md` (directory map).

## Bleeding-edge automation target

Prefer Rust-backed tooling where practical: `uv` for dependency management, `ruff`
for lint/format/imports, `ty` for type checking, `typos` for spelling, `zizmor` for
GitHub Actions security, `taplo` for TOML, `actionlint` for workflow syntax.

## Arrow and Polars baseline

All tabular work uses Polars + PyArrow (no pandas). Manifests are emitted as both
JSON and Parquet; the read-only DuckDB export is Parquet-backed.
