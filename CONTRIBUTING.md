# Contributing

## Commit Format

Use [Conventional Commits](https://www.conventionalcommits.org/) for every change on
`main`. `release-please` uses these messages to decide the next SemVer version,
update `CHANGELOG.md`, and create GitHub Releases.

Common prefixes:

- `feat:` for user-visible functionality or new archive capabilities.
- `fix:` for bug fixes.
- `docs:` for documentation-only changes.
- `test:` for test-only changes.
- `refactor:` for behavior-preserving code changes.
- `chore:` for maintenance that should not affect runtime behavior.

Use `!` or a `BREAKING CHANGE:` footer for breaking changes.

Examples:

```text
feat: add release provenance generation
fix: keep version sources in sync
docs: document archive versioning axes
```

## Release Versioning

Release versions are package SemVer versions. They are distinct from dataset
publication versions, schema versions, Hugging Face revisions, and Zenodo DOIs.
Do not manually edit `VERSION`, `pyproject.toml`, or
`src/fyi_archive/version.py` for a release; let `release-please` update them in the
release PR.
