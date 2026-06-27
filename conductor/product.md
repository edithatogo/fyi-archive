# Product Context

## Project

**fyi-archive** — a read-only, full-site archive of
[fyi.org.nz](https://fyi.org.nz/), the New Zealand Official Information Act (OIA)
request register (Alaveteli), distributed to GitHub, Hugging Face, Zenodo, and OSF.

## Current source asset

- **Upstream:** `https://fyi.org.nz/` (Alaveteli; public read-only endpoints).
- **Capture tool:** [`fyi-cli`](https://github.com/edithatogo/fyi-cli) (this repo's
  companion; owns all network access).
- **This repo's role:** orchestration + distribution only — **no** fetching/archiving
  logic lives here.

## Product goal

A faithful, fully-automated, evidence-backed archive of the entire public surface of
fyi.org.nz: every request (metadata + rendered page + attachments) captured as
WARC/WACZ, mirrored live to Hugging Face, snapshotted annually to Zenodo with a DOI,
and mirrored to OSF, with dynamic versioning, releases, SBOM, and provenance.

## Priority order

1. **Storage first, analysis later.** Phase 1 is read-only capture + mirroring. No
   OCR, normalisation, or NLP (explicit non-goal; future tracks).
2. **Historical before prospective.** Seed the full historical corpus, then set up
   the ongoing daily sync.
3. **Faithful over convenient.** WARC/WACZ is the source of truth; structured
   manifests are derived.
4. **Automated + bleeding-edge.** Fully CI/CD driven; current best-in-class tooling.

## Target users

- NLP / legal-tech researchers training models on NZ government text.
- Journalists and transparency researchers.
- Policy analysts and public-interest technologists.

## Core capabilities

| capability | owner |
| --- | --- |
| Bulk site enumeration | `fyi-cli` |
| Faithful capture (json + html + attachments → WARC/WACZ) | `fyi-cli` |
| Content-addressed archival diff | `fyi-cli` |
| Archive health / doctor | `fyi-cli` |
| Historical-seed orchestration + workflow | `fyi-archive` |
| Prospective daily sync + HF hash-verify | `fyi-archive` |
| Multi-mirror publish (HF/Zenodo/OSF) + metadata + DuckDB | `fyi-archive` |
| Versioning, releases, SBOM, provenance | `fyi-archive` |

## Non-goals for initial setup

- No text extraction, OCR, or normalisation.
- No write/submit operations against fyi.org.nz.
- No analysis, search index, or API serving the archived data (read-only store).
- Reimplementation of fetch logic that belongs in `fyi-cli`.

## Data ethics

Read-only capture of a third-party service. Rate-limited, `robots.txt`-aware,
contactable `User-Agent`. See `docs/ethics-and-compliance.md` and `NOTICE.md`.

## Versioning, CI/CD, and provenance target

The product target is a SOTA, evidence-backed automation system: SemVer for package/CLI
behaviour, independent dataset and schema versions, manifest-hash release evidence,
Hugging Face revision tracking, Zenodo DOI snapshots, protected production
publication, and artifact attestations or SLSA-style provenance for release outputs.
