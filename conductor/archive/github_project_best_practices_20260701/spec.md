# Track: GitHub project best practices and workflow maximization
Track ID: `github_project_best_practices_20260701`

## Goal

Make the `fyi-archive` project boards, the RIOPA umbrella project, and the source
repository boards use GitHub Projects v2 as natively as possible:

- built-in auto-add workflows where GitHub can add items itself,
- built-in status and auto-archive workflows for lifecycle management,
- GraphQL mutations for field and workflow state management,
- saved views and metadata that support real board slicing,
- and a custom mirror script only for cross-project portfolio synchronization.

## Background

The current project setup already mirrors work into the RIOPA umbrella board.
This track tightens that setup so GitHub Projects is the primary workflow surface
instead of a thin wrapper around manual updates.

## Scope

- Standardize the project metadata model across the source repo board and RIOPA.
- Prefer built-in project workflows for status changes, item lifecycle, and auto-add.
- Use GraphQL mutations for field updates, workflow state, and status updates.
- Add or refine saved views that split the board by source, status, and lifecycle.
- Keep the custom sync script limited to cross-project portfolio mirroring.
- Document the best-practice operating model in the repo.

## Out of scope

- Replacing GitHub Projects with a separate tracking system.
- Implementing a true nested-project feature, which GitHub does not support.
- Moving capture or archival logic out of `fyi-cli`.

## Acceptance criteria

- [x] Source boards use built-in auto-add / auto-close / auto-archive workflows where GitHub supports them.
- [x] RIOPA has metadata and saved views that can slice the portfolio by source and status.
- [x] GraphQL-based project mutations are the documented path for field and status management.
- [x] The custom mirror script is clearly scoped to cross-project synchronization only.
- [x] The repo documents the GitHub Projects operating model and its limitations.
