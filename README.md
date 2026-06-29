# fyi-archive

> Work in progress toward a **read-only, full-site archive** of [fyi.org.nz](https://fyi.org.nz/) — the New
> Zealand Official Information Act (OIA) request register (Alaveteli) — into
> **GitHub**, **Hugging Face**, **Zenodo**, and **OSF**.

[![CI](https://github.com/edithatogo/fyi-archive/actions/workflows/tests.yml/badge.svg)](https://github.com/edithatogo/fyi-archive/actions/workflows/tests.yml)
[![Quality](https://github.com/edithatogo/fyi-archive/actions/workflows/code_quality.yml/badge.svg)](https://github.com/edithatogo/fyi-archive/actions/workflows/code_quality.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12+-blue)](https://www.python.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

```mermaid
flowchart LR
  A["fyi.org.nz<br/>(Alaveteli, read-only)"] -->|public endpoints| B["fyi-cli<br/>enumeration + WARC/WACZ capture"]
  B -->|drives| C["fyi-archive<br/>orchestration + manifests"]
  C --> D["Hugging Face<br/>(live, revised)"]
  C --> E["Zenodo<br/>(annual DOI snapshot)"]
  C --> F["OSF<br/>(project mirror)"]
  C --> G["GitHub<br/>(code + releases + SBOM)"]
```

## Architecture (two-repo split)

| repo | role |
| --- | --- |
| [`fyi-cli`](https://github.com/edithatogo/fyi-cli) | **Capture tool.** Owns all network access: full-site enumeration, faithful WARC/WACZ capture (request JSON, rendered HTML, attachments), content-addressed dedup, archival content diff, archive health. |
| **`fyi-archive`** (this repo) | **Orchestration + distribution.** Thin consumer of `fyi-cli` commands. Planned scope includes historical seed, daily sync, multi-mirror publish, mirror adapters (HF/Zenodo/OSF), metadata (Croissant/Frictionless), DuckDB export, versioning/releases, and provenance. Contains **no** fetching/archiving logic. |

## Initial phase — read-only storage

The first phase is **storage only**: capture and mirror the public site faithfully,
with **no** analysis, OCR, or normalisation. (Those are future tracks.)

## Current status

This repository currently contains the orchestration skeleton, CI/quality gates,
release-please scaffolding, a preliminary `doctor` command, and Conductor plans.
It does **not** yet contain a completed historical FYI backfill, a populated
manifest, HF/Zenodo/OSF publisher implementations, or published archive artifacts.

## Directory structure

```
fyi-archive/
├── src/fyi_archive/      # orchestration CLI + mirror adapters (thin)
├── scripts/              # version consistency, SBOM
├── tests/
├── schemas/              # manifest, changes, croissant JSON Schemas
├── metadata/             # Croissant / Frictionless / schema.org (generated)
├── manifests/            # committed schema + placeholders (data lives on mirrors)
├── docs/                 # architecture, ethics, provenance
├── data/   (gitignored)  # raw WARC/WACZ + derived records + sync state
├── dist/   (gitignored)  # release bundles, DuckDB, SBOM, provenance
├── conductor/            # Conductor project context + tracks
└── .github/workflows/    # CI, sync, publish, release, security
```

## Data sources

| source | status | capture |
| --- | --- | --- |
| `fyi.org.nz` requests | target | JSON + HTML + attachments → WARC/WACZ (via `fyi-cli`) |
| `fyi.org.nz` authorities (bodies) | target | bodies spreadsheet → `manifests/authorities.json` |
| `fyi.org.nz` search feeds | target | advanced-search Atom/JSON feeds for enumeration |

## Distribution channels

| channel | role | cadence |
| --- | --- | --- |
| **Hugging Face** (`edithatogo/fyi-archive-nz`) | planned live, content-revised dataset | planned daily |
| **Zenodo** | planned DOI snapshot, draft-first and gated | planned annual |
| **OSF** | planned project + components mirror | planned on release |
| **GitHub Releases** | code releases via release-please; archive artifact attachments still planned | per release |

## Workflows

| workflow | purpose |
| --- | --- |
| `tests.yml` / `code_quality.yml` | CI: ruff, ty, pytest+cov, typos, taplo, actionlint, zizmor |
| `archive_health_monitor.yml` | scheduled preliminary archive health report |
| `validate_metadata.yml` | preliminary parity-count check; real mirror API checks still planned |
| `historical_seed.yml` | planned manual / fan-out historical backfill (drives `fyi-cli`) |
| `hf_sync.yml` | planned daily incremental sync to HF, with SHA-256 verify |
| `publish_archives.yml` | planned multi-mirror publish (HF/Zenodo/OSF) + build-provenance |
| `zenodo_publish.yml` | planned gated Zenodo DOI publish (`environment: zenodo-production`) |
| `release.yml` | release-please SemVer + changelog + GitHub Release |
| `codeql.yml` / `scorecard.yml` | security |
| `mirror_sync.yml` | push to secondary git mirror |

## Required GitHub Actions secrets

```
HF_TOKEN
ZENODO_TOKEN
ZENODO_SANDBOX_TOKEN        # optional, for draft rehearsal
OSF_TOKEN
GIT_MIRROR_SSH_PRIVATE_KEY  # if secondary mirror enabled
```

## Repository variables

```
HF_REPO_ID            = edithatogo/fyi-archive-nz
FYI_ARCHIVE_BASE_URL  = https://fyi.org.nz
ARCHIVE_TITLE         = fyi-archive (fyi.org.nz OIA register)
ARCHIVE_LICENSE       = MIT
```

See [`.env.example`](.env.example) for the local-run equivalents.

## Local setup

```bash
uv sync --extra dev          # from the lockfile
uv run pytest -q
make quality                 # ruff + ty + typos + taplo + actionlint + zizmor
```

> `fyi-cli` is referenced as a local path dependency (`../fyi-cli`); clone it
> alongside this repo inside the `legal-nz` workspace.

## Maintenance checklist

- **Weekly:** review archive health once `hf_sync.yml` exists; confirm mirror parity.
- **Monthly:** review Renovate PRs; rotate any tokens nearing expiry.
- **Annually:** trigger the planned Zenodo DOI snapshot workflow; update `CITATION.cff`.

## Ethics & compliance

Read-only capture only. Rate-limited, `robots.txt`-aware, contactable `User-Agent`.
See [`docs/ethics-and-compliance.md`](docs/ethics-and-compliance.md) and
[`NOTICE.md`](NOTICE.md).

## License

[MIT](LICENSE). Archived content remains © its respective contributors / fyi.org.nz;
this project preserves it for research and transparency only.

## Related projects

| repo | description |
| --- | --- |
| [`fyi-cli`](https://github.com/edithatogo/fyi-cli) | Capture tool (enumeration + WARC/WACZ) |
| [`corpus-law-nz`](https://github.com/edithatogo/corpus-legislation-nz) | NZ legislation corpus |
| [`corpus-nz-hansard`](https://github.com/edithatogo/corpus-nz-hansard) | NZ Hansard corpus |
| [`hathi-nz`](https://github.com/edithatogo/hathi-nz) | HathiTrust NZ corpus |
| [`sm-govt-nz`](https://github.com/edithatogo/sm-govt-nz) | NZ govt social-media archive |
