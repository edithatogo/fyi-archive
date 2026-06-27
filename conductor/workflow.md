# Project Workflow

## Guiding principles

1. **The plan is the source of truth.** All work is tracked in `plan.md` per track.
2. **Two-repo discipline.** Capture logic goes in `fyi-cli`; orchestration/mirror
   logic goes here. If a change fetches from the network or writes WARC/WACZ, it does
   not belong in this repo — open a track in `fyi-cli` instead.
3. **Storage first.** Phase 1 is read-only capture + mirroring; no analysis.
4. **Test-driven.** Write tests before implementing functionality.
5. **CI-aware.** Prefer non-interactive commands; `uv sync --frozen`.

## Standard task workflow

1. **Select task** from the active track's `plan.md`, in order.
2. **Mark in progress** (`[ ]` → `[~]`).
3. **Red phase:** write a failing test defining the expected behaviour.
4. **Green phase:** implement the minimum to pass.
5. **Refactor** under test.
6. **Verify coverage** (`make test-cov`).
7. **Document deviations**, then commit and mark `[x]` with the commit SHA.

## Validation expectations

- `make quality` passes (ruff, ty, typos, taplo, actionlint, zizmor).
- `make test-cov` passes with `fail_under`.
- `scripts/check_version_consistency.py` passes.
- New workflows pass `actionlint` and `zizmor`.

## External service workflow

- All network capture is delegated to `fyi-cli`.
- Mirror publishing is **draft-first**; production Zenodo DOI publish is gated behind
  `environment: zenodo-production` and an explicit confirmation string.
- HF sync re-downloads the remote manifest and verifies SHA-256 against local; the
  job fails on mismatch.

## Quality gates

| gate | tool | command |
| --- | --- | --- |
| lint + format | ruff | `make lint format` |
| types | ty | `make typecheck` |
| tests + coverage | pytest | `make test-cov` |
| spelling | typos | `make spell` |
| workflows | actionlint + zizmor | `make workflow-syntax workflow-audit` |
| deps | deptry | `make dependency-check` |
| SBOM | cyclonedx | `make sbom` |

## Commit guidelines

Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`).
`release-please` consumes these to produce SemVer bumps, `CHANGELOG.md`, and GitHub
Releases automatically.
