# Release Notes

All notable releases are documented here. Per-release changelogs are generated
automatically from [Conventional Commits](https://www.conventionalcommits.org/) by
`release-please` and also appear on the
[GitHub Releases](https://github.com/edithatogo/fyi-archive/releases) page.

## [Unreleased]

### Added

- Initial repository scaffold: standalone git repo, `pyproject.toml` (uv, ruff, ty),
  conductor setup, quality tooling (pre-commit, markdownlint, vale, taplo, typos,
  zizmor, actionlint), Renovate.
- Conductor tracks defined: `repo_bootstrap`, `historical_seed_orchestration`,
  `prospective_sync_orchestration`, `multi_mirror_publish`, `observability_quality`.
- Companion capability tracks added to `fyi-cli`: `bulk-site-enumeration`,
  `faithful-archive-capture`, `archival-content-diff`, `archive-health-doctor`.

### Notes

- The first release will be cut automatically by `release-please` once a
  `feat:` commit lands on `main`.

[Unreleased]: https://github.com/edithatogo/fyi-archive/compare/v0.1.0...HEAD
