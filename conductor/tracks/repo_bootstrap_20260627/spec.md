# Track: Repo bootstrap
Track ID: `repo_bootstrap_20260627`

## Goal

Stand up the standalone `fyi-archive` git repository with the full family-conformant
scaffold and wire it into the `legal-nz` workspace as a submodule, mirroring how the
sibling archives (`corpus-law-nz`, `hathi-nz`, `sm-govt-nz`) are wired.

## Background

The GitHub remote `edithatogo/fyi-archive` exists but is empty (no default branch).
Locally, `fyi-archive/` was a plain subfolder of the `legal-nz` monorepo. This track
makes it its own repo on branch `main`, pushes the scaffold, and registers it as a
workspace submodule.

## Scope

- `git init -b main` with local identity (Dylan Mordaunt / edithatogo noreply).
- Root config: `pyproject.toml` (uv, ruff, ty, family rule set), `VERSION`,
  `.python-version`, `Makefile`, `renovate.json`, `.gitignore`, `.env.example`.
- Quality tooling: `.pre-commit-config.yaml`, `.markdownlint.json`, `.vale.ini`.
- Legal/metadata: `LICENSE` (MIT), `NOTICE.md`, `SECURITY.md`, `CITATION.cff`,
  `DATASET_CARD.md`, `.zenodo.json`, `RELEASE_NOTES.md`.
- README with badges, mermaid architecture, directory map, workflows table,
  secrets/vars, maintenance checklist, ethics note.
- Package skeleton: `src/fyi_archive/{__init__,version,cli(stub)}.py` + version smoke
  test + `scripts/check_version_consistency.py`.
- Schemas: `schemas/manifest.schema.json`, `schemas/changes.schema.json`.
- Docs: `docs/README.md` (architecture), `docs/ethics-and-compliance.md`,
  **`docs/copyright-and-licensing.md`** (NZ copyright provisions with citations —
  Copyright Act 1994 ss.2/26/27, IPONZ, NZGOAL; satisfies R-30; takedown process R-32).
- Conductor: full `conductor/` set + this and the other four tracks.

## Out of scope

- Any network fetching or capture (that's `fyi-cli`).
- Implementing the orchestration CLI subcommands (later tracks).
- Pushing/merging beyond the first scaffold commit (gated on review).

## Acceptance criteria

- [ ] `git -C fyi-archive` reports branch `main`; `git remote -v` points at
      `https://github.com/edithatogo/fyi-archive.git`.
- [ ] `uv sync --extra dev` succeeds locally.
- [ ] `make lint format typecheck test` passes.
- [ ] `scripts/check_version_consistency.py` passes (VERSION == pyproject == package).
- [ ] README renders; badges reference real workflow files.
- [ ] `legal-nz/.gitmodules` contains an `fyi-archive` entry consistent with siblings.
- [ ] First scaffold commit pushed to `main` on the remote.

## Risks

- OneDrive path with spaces → quote all paths; prefer the dedicated read/edit tools.
- Family tooling (`ty`, `taplo`, `actionlint`, `zizmor`) may not be on PATH locally;
      CI is the authoritative gate, `make` targets degrade gracefully where a tool is
      absent.
