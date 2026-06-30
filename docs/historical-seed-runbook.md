# Historical Seed Runbook

The historical seed workflow is the bounded, resumable entrypoint for building the
first FYI archive corpus. Capture itself belongs to `fyi-cli`; this repository owns
orchestration, ledger state, manifest assembly, and release evidence.

## Current Mode

Live backfill is driven by `fyi-cli` ID-space discovery/capture and remains bounded by
request count, runtime, and disk caps. Dry-run mode is still available for workflow
validation; it writes deterministic derived records and exercises ledger, manifest,
and provenance paths without network access.

## Local Smoke

```bash
uv run fyi-archive seed run --dry-run --max-requests 50 --max-runtime-minutes 30 --max-disk-gb 5
uv run fyi-archive manifest build --fyi-cli-version 1.0.0
uv run python scripts/gen_provenance.py \
  --artifact manifests/latest_manifest.json \
  --artifact manifests/latest_manifest.parquet \
  --artifact manifests/authorities.json \
  --fetch-label historical-seed-smoke
```

The seed ledger is `data/_state/ledger.jsonl`. Re-running the seed skips request IDs
already marked `completed`.

## Caps

- `--max-requests`: stops before processing more new requests.
- `--max-bytes`: stops once accumulated generated/captured output bytes reach the cap.
- `--max-runtime-minutes`: stops between requests when the runtime cap is reached.
- `--max-disk-gb`: preflight minimum free disk space before starting.

All caps preserve the ledger entries already written.

## GitHub Actions

Use `Automated Historical Backfill` for unattended corpus backfilling. It persists
progress in the `FYI historical backfill state` GitHub issue, dispatches bounded
`Historical Backfill Batch` worker runs, and advances `next_id` only after the worker
batch has been merged and verified. Defaults are intentionally conservative: scheduled runs dispatch a small
number of worker batches, and each worker keeps its own chunk, request, runtime, and
disk caps.

For controller smoke tests, set `dry_run=true` and use a temporary `state_label` such
as `fyi-backfill-state-smoke` so the test does not advance the live corpus cursor.

Use `Historical Backfill Batch` manually for targeted repair, replay, or smoke testing.
The workflow uploads the ledger, raw/derived records, manifest outputs, and provenance
as artifacts. `Merge Backfill Artifacts` runs automatically after successful worker
runs and can also be dispatched manually to combine one worker run's chunk manifests
into a single merged manifest artifact. The monthly publish workflow also emits a
`backfill_verification.json` report in `dist/` and `versions/` that compares
dispatched request IDs, captured counts, merged counts, and published counts across
GitHub Actions, Hugging Face, and Zenodo.

## Full Crawl Shape

Do not run the whole FYI corpus as one monolithic GitHub Actions job. Use the automated
controller to progress through the request-ID range in resumable windows. Increase
`batch_span`, `max_batches`, or worker caps only after observing stable runtime,
failure rate, and artifact size for smaller runs.
