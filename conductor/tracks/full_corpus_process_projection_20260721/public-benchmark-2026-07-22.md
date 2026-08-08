# Public snapshot benchmark

Date: 2026-07-22

Inputs were downloaded from the public Hugging Face dataset
`edithatogo/fyi-archive-nz` at the `main` revision:

- `manifests/latest_manifest.json`
- `process-events/events.jsonl`

The non-publishing runner `scripts/benchmark_process_projection.py` completed
in `0.337804` seconds and verified the generated projection checksums
(`29ab8015eb0411a702735a63e0c3ea0f8f6621fcdbfccd1616f6467ded9d48fd`).

The result is **not accepted as full-corpus evidence**. The manifest reports
`33,217` requests, while the process-event input materializes only `1` case
and `2` events. Consequently `request_count_reconciles=false`. This is a
real public-deposit parity failure requiring the fyi-cli/fyi-archive backfill
and continuation outputs to be regenerated before the full-corpus benchmark
or Conductor closure can be claimed.
