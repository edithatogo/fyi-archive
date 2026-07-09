# Track: GitHub project mirror and RIOPA sync
Track ID: `github_project_sync_20260701`

## Goal

Mirror the `fyi-archive` development surface, issues, and roadmap into the repo
project at `https://github.com/users/edithatogo/projects/4`, and keep that board
synced into the umbrella project "Rare Insights on Open Policy from Aotearoa"
(`RIOPA`) alongside the sibling boards `projects/1` and `projects/3`.

## Background

GitHub Projects v2 does not support true nested projects. The practical model is
item-level mirroring: issues and pull requests from the contributing boards are
added to the umbrella project so it can act as the portfolio view.

## Scope

- Create and maintain the repo-linked `fyi-archive` project.
- Mirror issue and PR URLs from the source project boards into `RIOPA`.
- Keep the umbrella project description and readme explicit about the sync model.
- Provide a verification path that reports source counts, target counts, and
  remaining gaps.

## Out of scope

- Rewriting GitHub Projects support as a native nested-project feature.
- Synchronizing classic projects or non-item board metadata.
- Moving issue ownership between repositories.

## Acceptance criteria

- [x] The `fyi-archive` repo project is linked and populated with its active issue / PR items.
- [x] The RIOPA umbrella project contains mirrored items from repo project 4 plus projects 1 and 3.
- [x] A repo script can report the difference between source items and target items.
- [x] A scheduled workflow exists for repeatable syncs.
- [x] The project metadata explains that the board is mirrored, not nested.
