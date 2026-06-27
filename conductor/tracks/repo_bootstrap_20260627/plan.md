# Plan: repo_bootstrap_20260627

## Phase 1: Repository & identity

- [x] 1.1 `git init -b main`; set local `user.name`/`user.email`.
- [x] 1.2 Add remote `origin -> https://github.com/edithatogo/fyi-archive.git`.
- [x] 1.3 Create directory skeleton (`src/`, `scripts/`, `tests/`, `schemas/`,
      `metadata/`, `manifests/`, `docs/`, `data/`, `dist/`, `.github/workflows/`,
      `conductor/`).

## Phase 2: Root configuration

- [x] 2.1 `VERSION`, `.python-version`.
- [x] 2.2 `pyproject.toml` (uv, ruff family rules, ty, coverage, pytest, family
      `[tool.legal_nz]`, `[tool.uv.sources]` path deps on `fyi-cli` + `nlp-policy-nz`).
- [x] 2.3 `.gitignore`, `.env.example`.
- [x] 2.4 `LICENSE`, `NOTICE.md`, `SECURITY.md`, `CITATION.cff`, `DATASET_CARD.md`,
      `.zenodo.json`, `RELEASE_NOTES.md`.
- [x] 2.5 `Makefile`, `renovate.json`, `.pre-commit-config.yaml`, `.markdownlint.json`,
      `.vale.ini`.
- [x] 2.6 `README.md` (badges, mermaid, directory map, workflows, secrets/vars,
      maintenance, ethics, related projects).

## Phase 3: Package skeleton + schemas + docs

- [x] 3.1 `src/fyi_archive/{__init__,version,cli(stub)}.py`.
- [x] 3.2 `tests/test_version.py` (smoke).
- [x] 3.3 `scripts/check_version_consistency.py`.
- [x] 3.4 `schemas/{manifest,changes}.schema.json`, `manifests/.gitkeep`.
- [x] 3.5 `docs/README.md`, `docs/ethics-and-compliance.md`,
      **`docs/copyright-and-licensing.md`** (Copyright Act 1994 ss.2/26/27, IPONZ,
      NZGOAL; takedown process) — satisfies R-30, R-32.

## Phase 4: Conductor setup

- [x] 4.1 `setup_state.json`, `product.md`, `product-guidelines.md`, `tech-stack.md`,
      `workflow.md`, `tracks.md`.
- [x] 4.2 `maturity-checklist.md`, `quality-maintenance-checklist.md`,
      `improvement-backlog.md`, `learning-log.md`, `code_styleguides/README.md`.
- [x] 4.3 This track + the four other tracks (spec + plan each).

## Phase 5: Validate, commit, push, submodule
- [x] 5.1 `scripts/check_version_consistency.py` passes.
- [x] 5.2 First scaffold commit on `main` (conventional-commit message).
- [x] 5.3 `git push -u origin main`.
- [x] 5.4 Add `fyi-archive` submodule entry to `legal-nz/.gitmodules` (branch `main`)
      consistent with siblings; commit in the workspace repo.
