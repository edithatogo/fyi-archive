# Plan

GitHub issue: https://github.com/edithatogo/fyi-archive/issues/189

- [x] Audit current versus latest compatible dependencies. (98a1c68)
- [x] Define production Python 3.12 and non-blocking 3.13/3.14 canary environments. (98a1c68)
- [x] Add stable blocking Ruff and advisory preview Ruff checks. (98a1c68)
- [~] Add strict basedpyright/ty evidence and Pydantic v2/JSON Schema gates. The initial basedpyright baseline is 974 findings and remains non-blocking.
- [x] Add strict freshness, provenance, digest, SBOM, and cross-repo contract gates. (98a1c68)
- [x] Extend mutation/property/security harness evidence without silent upgrades. (98a1c68)

## Review evidence (2026-07-14)

- Passed: Ruff lint and format, `ty check src`, full tests (`202 passed, 1
  skipped`), coverage (`90.31%`), `uv lock --check`, `uv tree --outdated
  --all-groups --locked`, SBOM generation, and version consistency.
- Remaining blocker: `basedpyright` reports the documented 974-finding
  baseline, so the strict typing task remains non-blocking and in progress.
- Environment/tooling limitation: local `typos` executable is unavailable;
  `deptry src` reports 27 existing dependency-use findings from dynamic,
  optional, and development-only paths. These require a separate dependency
  hygiene pass rather than silent removals in this track.
