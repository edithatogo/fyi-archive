# Plan

GitHub issue: https://github.com/edithatogo/fyi-archive/issues/189

- [x] Audit current versus latest compatible dependencies.
- [x] Define production Python 3.12 and non-blocking 3.13/3.14 canary environments.
- [x] Add stable blocking Ruff and advisory preview Ruff checks.
- [~] Add strict basedpyright/ty evidence and Pydantic v2/JSON Schema gates. The initial basedpyright baseline is 974 findings and remains non-blocking.
- [x] Add strict freshness, provenance, digest, SBOM, and cross-repo contract gates.
- [x] Extend mutation/property/security harness evidence without silent upgrades.
