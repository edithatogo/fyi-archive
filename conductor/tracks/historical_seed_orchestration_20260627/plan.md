# Plan: historical_seed_orchestration_20260627

## Phase 1: Orchestration surface (stubbed until fyi-cli lands)

- [x] 1.1 Add `fyi-archive seed` subcommand: parses window/cap inputs, shells to
      `fyi-cli` enumeration + capture, writes `data/_state/ledger.jsonl`.
- [x] 1.2 Resume logic: read ledger, skip completed request IDs; idempotent.
- [x] 1.3 Hard-cap enforcement (--max-requests/--max-bytes/--max-runtime-minutes/
      --max-disk-gb) with graceful abort + state flush.
- [x] 1.4 Unit tests for cap enforcement + resume (hypothesis on ledger parsing).

## Phase 2: Manifest assembly

- [x] 2.1 `fyi-archive manifest` reads the derived store, emits
      `manifests/latest_manifest.{json,parquet}` + `authorities.json`.
- [x] 2.2 Validate against `schemas/manifest.schema.json`; fail CI on schema error.
- [x] 2.3 Manifest meta records `fyi_cli_version` + `generated_at` + `source`.

## Phase 3: Workflow

- [x] 3.1 `historical_seed.yml` — disk precheck + date-window matrix fan-out +
      ledger reconciliation + artifacts (WACZ, manifest, provenance).
- [x] 3.2 `actionlint` + `zizmor` clean on the workflow.

## Phase 4: Smoke seed validation

- [x] 4.1 Dry-run smoke (≤50 requests, single window) on GHA; assert manifest rows.
- [!] 4.2 Full-path smoke including HF upload + remote manifest SHA-256 verify.
- [x] 4.3 Document the full-crawl runbook (windows, caps, expected duration) in
      `docs/`.

## Dependencies / blocking

- BLOCKED on `fyi-cli` tracks `bulk-site-enumeration` and `faithful-archive-capture`
  plus this repo's HF publisher from `multi_mirror_publish` for the full live smoke.
