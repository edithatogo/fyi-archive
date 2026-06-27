# Plan: historical_seed_orchestration_20260627

## Phase 1: Orchestration surface (stubbed until fyi-cli lands)

- [ ] 1.1 Add `fyi-archive seed` subcommand: parses window/cap inputs, shells to
      `fyi-cli` enumeration + capture, writes `data/_state/ledger.jsonl`.
- [ ] 1.2 Resume logic: read ledger, skip completed request IDs; idempotent.
- [ ] 1.3 Hard-cap enforcement (--max-requests/--max-bytes/--max-runtime-minutes/
      --max-disk-gb) with graceful abort + state flush.
- [ ] 1.4 Unit tests for cap enforcement + resume (hypothesis on ledger parsing).

## Phase 2: Manifest assembly

- [ ] 2.1 `fyi-archive manifest` reads the derived store, emits
      `manifests/latest_manifest.{json,parquet}` + `authorities.json`.
- [ ] 2.2 Validate against `schemas/manifest.schema.json`; fail CI on schema error.
- [ ] 2.3 Manifest meta records `fyi_cli_version` + `generated_at` + `source`.

## Phase 3: Workflow

- [ ] 3.1 `historical_seed.yml` — disk precheck + date-window matrix fan-out +
      ledger reconciliation + artifacts (WACZ, manifest, provenance).
- [ ] 3.2 `actionlint` + `zizmor` clean on the workflow.

## Phase 4: Smoke seed validation

- [ ] 4.1 Dry-run smoke (≤50 requests, single window) on GHA; assert manifest rows.
- [ ] 4.2 Full-path smoke including HF upload + remote manifest SHA-256 verify.
- [ ] 4.3 Document the full-crawl runbook (windows, caps, expected duration) in
      `docs/`.

## Dependencies / blocking

- BLOCKED on `fyi-cli` tracks `bulk-site-enumeration` and `faithful-archive-capture`.
