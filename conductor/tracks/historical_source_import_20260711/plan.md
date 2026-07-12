# Implementation plan

- [x] Define offline-only Morph and Internet Archive input contracts.
- [x] Normalize and deduplicate historical index records.
- [x] Record input checksums and retrieval metadata.
- [x] Add CLI script and focused tests.
- [x] Run the full archive quality gate.
- [x] Configure `MORPH_API_KEY` before the scheduled or manual workflow can run;
      the repository secret was present and the verified workflow run
      [29193301907](https://github.com/edithatogo/fyi-archive/actions/runs/29193301907)
      downloaded both inputs and produced a provenance-preserving index with
      8,712 deduplicated records.

## Evidence

Run `29193301907` completed successfully. Its retained artifact contains two
input records (Morph CSV and Internet Archive CDX JSON), checksums and retrieval
metadata, and `historical-source-index-v1` with `record_count=8712`.
