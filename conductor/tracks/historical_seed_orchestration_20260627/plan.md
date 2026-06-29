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
- [x] 4.2 Full-path smoke including HF upload + remote manifest SHA-256 verify
      (GHA run 28378172250 at 3d9296c; HF commit
      f13d7b22f97bfa5434e593edf871b69c18004b09; manifest SHA-256
      49aa057e7c02cdf50e71825c0b474734553e8799563a95e837a5a2a19a1c4718).
- [x] 4.3 Document the full-crawl runbook (windows, caps, expected duration) in
      `docs/`.

## Dependencies / blocking

- UNBLOCKED locally: `fyi-cli discover`, `fyi-cli capture`, `fyi diff`, and
  `fyi archive-health` are implemented with focused mocked tests.
- UNBLOCKED: full live proof passed on GHA run 28378172250, including capped
  FYI capture, HF upload + remote SHA-256 verification, Zenodo draft artifact
  verification, OSF artifact verification, evidence upload, and attestation.
