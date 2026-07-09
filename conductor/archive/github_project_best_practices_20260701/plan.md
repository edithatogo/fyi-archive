# Plan: github_project_best_practices_20260701

## Phase 1: Lock the project model

- [x] 1.1 Review the current GitHub Projects configuration for projects 1, 3, and 4.
- [x] 1.2 Record the supported best-practice patterns and GitHub limitations in the track spec.
- [x] 1.3 Define the board metadata that must be consistent across all projects.

## Phase 2: Maximize native project workflows

- [x] 2.1 Configure built-in auto-add workflows on each source repo board where GitHub supports them.
- [x] 2.2 Configure built-in status and auto-archive workflows for lifecycle management.
- [x] 2.3 Confirm the existing field model is sufficient for source, lifecycle, and roadmap slicing.
- [x] 2.4 Add or refine status updates on the boards so project health is visible in GitHub.

## Phase 3: Add board slices and automation hooks

- [x] 3.1 Create or refine saved views for source-specific and status-specific slices.
- [x] 3.2 Use GraphQL mutations to manage field values and workflow state from the repo automation.
- [x] 3.3 Update the mirror script so it only handles cross-project portfolio synchronization.
- [x] 3.4 Verify the umbrella board still mirrors the source boards after the workflow changes.

## Phase 4: Document and verify

- [x] 4.1 Document the GitHub Projects best-practice operating model in the README or docs.
- [x] 4.2 Add a verification note that explains which parts are GitHub-native and which are custom.
- [x] 4.3 Re-run the project sync and confirm counts, field values, and status updates remain stable.
