# Implementation plan

- [x] 1. Create the maintenance-hardening track and align project metadata.
- [x] 2. Refresh operational backlog, runbook, and status snapshots.
- [x] 3. Pin `fyi-cli` to the published `v1.2.0` release and make blocking quality gates strict; keep existing advisory scans explicit.
- [x] 4. Add bounded pending-batch re-queue planning with unit coverage.
- [~] 5. Run local tests and quality checks; verify the resulting GitHub Actions PR.

## Verification

- `uv run pytest -q`
- `make quality`
- `actionlint`
- `zizmor --min-severity medium .github/workflows`
