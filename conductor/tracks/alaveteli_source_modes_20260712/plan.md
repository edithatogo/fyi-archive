# Plan: alaveteli_source_modes_20260712

- [x] Add source-mode metadata to the instance registry.
- [x] Add offline Alaveteli JSON and Atom feed importers with checksums.
- [x] Add monthly Internet Archive CDX matrix for remaining deployments.
- [x] Run the historical-index workflow and inspect per-instance artifacts
      (run [29155701544](https://github.com/edithatogo/fyi-archive/actions/runs/29155701544):
      16 artifacts, 13 non-empty indexes, 3 empty-but-valid indexes).
- [x] Add bounded archived-page core-data extraction with explicit extraction status.
- [ ] Add official-dataset and operator-export adapters as sources are identified.
- [ ] Use fyi-cli feed discovery for candidates whose feed endpoint becomes reachable.
