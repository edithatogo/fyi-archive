# GitHub Projects operating model

Verified on 2026-07-01 for the `fyi-archive` workspace.

## Intent

GitHub Projects v2 is the primary workflow surface for the archive roadmap. The
repo keeps the source boards and the umbrella RIOPA project aligned, but the
custom automation is intentionally narrow:

- GitHub-native workflows handle item lifecycle on the source boards.
- GraphQL mutations manage item field updates and project status updates.
- A custom mirror script only performs cross-project portfolio synchronization.

## Current project shape

- `projects/1`: `rulespec-nz coverage ledger`
- `projects/3`: `nlp-policy-nz Conductor Roadmap`
- `projects/4`: `Rare Insights on Open Policy from Aotearoa` (`RIOPA`)

The source boards already expose the default built-in workflows:

- auto-add sub-issues to project
- auto-close issue
- item added to project
- item closed
- pull request linked to issue
- pull request merged

## Metadata model

The umbrella project keeps a `Mirror source` field with the values:

- `rulespec-nz`
- `nlp-policy-nz`
- `fyi-archive`
- `other`

That field is the stable provenance marker for mirrored items.

## Views

GitHub Projects views are managed in the UI. The repo cannot create views through
the current GraphQL surface, so saved views should be created manually and kept
stable there.

Recommended views for the umbrella project:

- `All items`
- `By source`
- `By status`
- `Lifecycle queue`
- `Recently updated`

Recommended filters:

- `Mirror source:rulespec-nz`
- `Mirror source:nlp-policy-nz`
- `Mirror source:fyi-archive`
- `Status:Todo`
- `Status:In Progress`
- `Status:Done`

## Automation contract

The mirror script should stay limited to:

- adding missing issue and pull-request items to the umbrella project,
- updating `Mirror source` through `updateProjectV2ItemFieldValue`,
- posting a project status update through `createProjectV2StatusUpdate`,
- and reporting counts and workflow coverage for verification.

The script must not try to emulate GitHub-native workflows or invent nested
projects. Those remain GitHub-managed or UI-managed concerns.

## Verification

The sync workflow writes a JSON project report and posts a GitHub Projects
status update after a successful apply run. The report captures:

- source and target item counts,
- field coverage,
- workflow coverage,
- view counts,
- and the current status update count.

If GitHub adds view creation or workflow mutation support later, this document
should be updated to move those steps out of manual setup.
