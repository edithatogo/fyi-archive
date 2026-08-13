# Track: Security, quality, and fuzzing hardening
Track ID: `security_quality_fuzzing_20260813`
Satisfies: **R-18**

## Goal

Continuously exercise untrusted archive, manifest, path, and parser boundaries with
deterministic property tests and bounded coverage-guided fuzzing.

## Scope

- Strengthen Hypothesis coverage over production path invariants in pull requests.
- Add Atheris harnesses for catalog ZIPs, immutable archive packages, and historical manifests.
- Run short pull-request smoke and longer scheduled/manual campaigns with resource caps.
- Retain generated failure inputs without retaining source correspondence or credentials.
- Keep actions pinned, permissions read-only, dependency auditing blocking, and existing gates intact.

## Acceptance criteria

- [x] Production ZIP and historical manifest parsers enforce explicit size and path boundaries.
- [x] Hypothesis directly tests a production security invariant.
- [x] Three Atheris harnesses invoke production entry points with synthetic seeds.
- [x] Workflow and harness contracts are covered by deterministic tests.
- [x] Fuzz dependencies and all remote actions are pinned.
- [ ] Pull-request smoke and scheduled/manual campaigns are green on GitHub Actions.

## Data handling

Only synthetic generated inputs and crash artifacts are retained. Production correspondence,
attachments, tokens, and other source-derived payloads are prohibited from fuzz corpora.
