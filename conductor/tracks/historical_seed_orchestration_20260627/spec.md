# Track: Historical-seed orchestration
Track ID: `historical_seed_orchestration_20260627`

## Goal

Orchestrate a **resumable, date-windowed, capped** historical backfill of the entire
public surface of fyi.org.nz by *driving* `fyi-cli`'s new capture capabilities, and
assemble the initial manifest. This repo owns the orchestration + manifest assembly;
`fyi-cli` owns the actual fetching and WARC/WACZ writing.

## Prerequisites (in `fyi-cli`)

- `bulk-site-enumeration` — discover every request via advanced-search Atom/JSON feeds
  (date-windowed, paginated) + optional ID-space gap backfill.
- `faithful-archive-capture` — per request: JSON + HTML + attachments → WARC 1.1 +
  WACZ; content-addressed attachment dedup.

## Scope

- `historical_seed.yml` workflow: `workflow_dispatch` with inputs
  (`--date-from`, `--date-to`, `--max-requests`, `--max-bytes`,
  `--max-runtime-minutes`, `--max-disk-gb`, `--concurrency`, `--dry-run`).
- Disk-budget precheck; date-window **matrix fan-out** reconciled by
  `data/_state/ledger.jsonl`; resumable from that ledger on retry.
- Invoke `fyi-cli` to enumerate + capture each window.
- Assemble `manifests/latest_manifest.{json,parquet}` (+ `authorities.json`) from the
  captured WARC/derived store; validate against `schemas/manifest.schema.json`.
- Upload evidence + WACZ + `provenance.json` as artifacts.
- **Capped smoke seed:** one date window, `--max-requests 50`, `--dry-run`-capable,
  validating the full path (enumerate → capture → manifest → HF upload → SHA-256
  verify) before any full crawl.

## Out of scope

- Implementing enumeration or WARC/WACZ capture (that's `fyi-cli`).
- Multi-mirror publishing (see `multi_mirror_publish`).
- Analysis / OCR / normalisation (phase 1 non-goal).

## Acceptance criteria

- [x] `historical_seed.yml` runs to completion on a capped dry-run with no secrets
      errors and produces a populated `latest_manifest.json`.
- [x] Manifest validates against `schemas/manifest.schema.json`.
- [x] Re-running after interrupt resumes from `ledger.jsonl` (no re-capture of done IDs).
- [x] Hard caps (`--max-requests`/`--max-bytes`/`--max-runtime-minutes`/`--max-disk-gb`)
      are enforced and documented.
- [!] Capped smoke seed (≤50 requests) completes the full path including HF upload and
      SHA-256 verify.

## Risks

- `fyi-cli` discovery/capture commands now exist; this track remains blocked on the
  remaining hardening and a live seeded corpus + HF verification run.
- fyi.org.nz pagination edge cases (empty windows, redirects) → handled in
  `fyi-cli`'s enumeration, asserted here via manifest row counts.
- Long crawl vs the 6h job limit → mitigated by date-window fan-out + resume ledger.
