# Implementation plan

- [x] Refresh maturity checklist evidence and timestamps.
- [x] Refresh improvement backlog operational statuses.
- [x] Verify repository and workflow state.
- [x] Merge the protected-branch documentation PR.

Evidence: PR #175 merged into `main` as commit `d11d429`; the repository is
clean, no pull requests remain open, and the retained OSF and health-monitor
workflow evidence is current.

## 2026-08-01 reconciliation

- [x] Correct the August one-record Hugging Face regression through Hub PR 2;
  the restored manifest and Parquet digests match retained revision `a462fe7`,
  and Dataset Viewer exposes 33,217 rows without pending or failed conversion.
- [x] Record green archive-health run `30692982151` after hosted restoration.
- [x] Repair and validate fail-closed CDX error-object handling: bounded run
  `30692890453` completed all 16 independent Alaveteli jobs successfully.
- [ ] Project sync remains credential-gated after run `30692889152`: the
  existing workflow PAT authenticates but cannot access Project 4. Provision a
  dedicated `RIOPA_PROJECT_TOKEN` with Projects read/write scope, then rerun
  exactly once.

The older closeout sentence above is retained as historical evidence, not a
claim about the current open-PR or hosted-service state.
