# Specification: Full-corpus process projection and continuation

GitHub issue: https://github.com/edithatogo/fyi-archive/issues/196  
Parent epic: https://github.com/edithatogo/foi-process/issues/36  
Upstream issue: https://github.com/edithatogo/fyi-cli/issues/231

## Overview

Create a separately identified derived layer containing process cases, events,
attachment metadata, revisions, and coverage information for every captured request.
The layer supports deterministic full backfill and daily continuation without replacing
or conflating immutable archive manifests and raw WARC/WACZ evidence.

## Functional requirements

- Validate the pinned upstream process-event contract.
- Produce partitioned Parquet for cases, events, attachment metadata, and revisions.
- Produce coverage, checksum, source-revision, rights, and snapshot-lineage manifests.
- Resume full-corpus backfill and merge incremental changes deterministically.
- Propagate corrections, retractions, and takedown tombstones.
- Expose Dataset Viewer-compatible configurations and splits.
- Preserve source ordering and stable identifiers across shards and compaction.

## Storage and publication boundary

Raw evidence remains in the archive layer. The process projection excludes message
bodies, requester identity, request titles, OCR text, embeddings, and attachment bytes.
Projection publication remains separately gated even when local generation succeeds.

## Acceptance criteria

- Request coverage reconciles exactly to a pinned archive manifest, with explicit exclusions.
- Event totals reconcile to source timeline totals.
- Full replay and incremental merge produce identical active rows and hashes.
- Repeated generation is deterministic and shard paths are stable.
- Dataset Viewer validates all intended configs, splits, and Parquet shards.
- Removal and replacement tests prove that stale public rows cannot survive recursively.

## Out of scope

- Process mining algorithms and dashboard UI.
- Raw WARC, correspondence, OCR, NLP, or embedding publication.
- Paid hosted compute or transactional serving infrastructure.
