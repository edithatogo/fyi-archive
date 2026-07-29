# Separate FOI site Internet Archive snapshots

The `foi_site_internet_archive.yml` workflow refreshes a cumulative Wayback CDX
snapshot every week for each configured FOI site. It does not contact an origin
site and it cannot publish data remotely.

Each site has:

- a stable, filesystem-safe archive identity;
- one or more site-specific Wayback URL patterns;
- an independent workflow artifact named with that site identity and run ID;
- a manifest recording checksums, retrieval failures, source, country, site
  kind, and the explicit `origin_contacted: false` boundary.

The inventory combines every `internet_archive`-enabled entry in
`fyi_archive.instances` with the additional and non-Alaveteli targets in
`configs/additional_foi_archive_sites.json`. Adding a site to either registry
automatically includes it in the next scheduled matrix.

Workflow artifacts are retained for 90 days. Durable publication to the
site-specific Hugging Face repositories is a separate, confirmation-gated
operation; a successful scheduled snapshot must not be described as published.

## Resume and verification controls

Resume-key chunks are hash-verified before reuse. The scheduled workflow has a
whole-pattern deadline and a shorter progress-stall deadline; a stall fails
closed while retaining any checkpoint already written. Progress logs contain
only the next-key SHA-256, never the raw cursor.

Retained artifacts can be independently checked and compared with earlier runs:

```console
uv run python scripts/verify_wayback_artifacts.py ARTIFACT_DIR... \
  --prior-root PRIOR_RUN_DIR \
  --baseline-root BASELINE_RUN_DIR \
  --output progress-index.json
```

The progress index deliberately reports `coverage_percentage: null`. Retained
record counts show observed checkpoint progress, not corpus coverage.

## Deterministic time partitions

Very large named-site queries may be split into contiguous, inclusive year
ranges. Closed ranges remain immutable and the final range is open-ended. Each
partition must be fetched with `--from-timestamp`, optional `--to-timestamp`,
and `--include-urlkey`; those settings form part of its checkpoint identity.

After every declared partition is complete, merge them with:

```console
uv run python scripts/merge_complete_wayback_partitions.py \
  --plan partition-plan.json \
  --root partition-artifacts \
  --output merged.json \
  --evidence merged-evidence.json
```

The plan uses schema `fyi-archive.wayback-partition-plan.v1`. Each partition
object declares `id`, `from_timestamp`, `to_timestamp`, `output`, and
`evidence`. The merger rejects gaps, overlaps, closed final ranges, incomplete
retrievals, changed headers, mismatched response hashes, and files outside the
declared root. It deduplicates by CDX `urlkey` and retains the earliest
timestamp. Partitioning remains an operator-controlled named-site improvement
until a bounded hosted trial passes; it does not create an automatic retry
loop.
