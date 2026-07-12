# Plan: alaveteli_source_modes_20260712

- [x] Add source-mode metadata to the instance registry.
- [x] Add offline Alaveteli JSON and Atom feed importers with checksums.
- [x] Add monthly Internet Archive CDX matrix for remaining deployments.
- [x] Run the historical-index workflow and inspect per-instance artifacts
      (run [29155701544](https://github.com/edithatogo/fyi-archive/actions/runs/29155701544):
      16 artifacts, 13 non-empty indexes, 3 empty-but-valid indexes).
- [x] Add bounded archived-page core-data extraction with explicit extraction status.
- [x] Run the bounded core-data smoke across all 16 historical-only deployments
      (run [29156598360](https://github.com/edithatogo/fyi-archive/actions/runs/29156598360):
      26 pages processed and extracted; 3 deployments had no replay pages).
- [x] Run the configured 25-page enrichment across all deployments
      (run [29188459178](https://github.com/edithatogo/fyi-archive/actions/runs/29188459178):
      306 pages processed, 174 extracted, 16 artifacts, 0 failures).
- [x] Add offline official-dataset and operator-export adapters; require public request URLs and retain file checksums.
- [x] Assess fyi-cli feed discovery for candidates whose feed endpoint becomes
      reachable. The 2026-07-12 probe against `quesabes.org` failed closed on
      non-JSON responses, so no feed promotion was made; the automated probe
      remains available for a future compatible endpoint.
