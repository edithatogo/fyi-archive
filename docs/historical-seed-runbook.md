# Historical Seed Runbook

The historical seed workflow is the bounded, resumable entrypoint for building the
first FYI archive corpus. Capture itself belongs to `fyi-cli`; this repository owns
orchestration, ledger state, manifest assembly, and release evidence.

## Current Mode

`fyi-cli` bulk enumeration and faithful WARC/WACZ capture commands are still pending,
so `fyi-archive seed run --dry-run` is the safe validation mode. Dry-run mode writes
deterministic derived records and exercises ledger, cap, manifest, and provenance
paths without network access.

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

Run `Historical Seed` manually. Keep `dry_run=true` until the required `fyi-cli`
capabilities exist. The workflow uploads the ledger, derived records, manifest outputs,
and provenance as artifacts.

## Full Crawl Shape

Once `fyi-cli` provides bulk enumeration and capture, use date windows small enough to
fit under the six-hour GitHub Actions limit. Prefer month-sized windows first, then
adjust based on observed request density and attachment volume. A full crawl should be
treated as a set of resumable windows rather than one monolithic job.
