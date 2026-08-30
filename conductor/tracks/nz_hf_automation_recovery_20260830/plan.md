# Implementation plan

- [x] Establish regression cases for exact failed owners, live/successful owners, stale observations, replacement and range conflicts.
- [x] Implement pure recovery transition and stop monitor redispatch while a lease exists.
- [x] Add serialized prepare/retain/recheck/apply workflow with default diagnosis-only mode and main-branch application guard.
- [x] Reproduce contaminated stdout, stale summary, path collision and cross-instance card failures.
- [x] Implement dedicated atomic summary, stderr diagnostics, strict card inputs and always-retained bounded execution receipt.
- [~] Run complete tests, repository quality and workflow validation; record host-tool limitations separately.
- [ ] Verify exact hosted CI, retained recovery artifact and real controlled lease recovery; observe subsequent progress without skipping work.
- [ ] Verify public manifest/card consistency and close only the completed repair scope.
