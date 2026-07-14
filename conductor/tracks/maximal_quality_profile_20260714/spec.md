# Maximal quality profile

Audit the archive as an evidence-producing pipeline: lockfile freshness,
strict typing, schema/property/mutation tests, provenance, digest checks, and
cross-repository release compatibility.

The production lock must remain deterministic. Freshness automation may report
new releases, but may not silently rewrite the lockfile. Stable Ruff, strict
typing, Pydantic v2/JSON Schema validation, property and mutation testing,
provenance/digest checks, SBOM generation, workflow security, and FOI-O/NLP
consumer-contract tests are release gates. Preview Ruff and Python 3.14 are
canary evidence until they pass the supported-runtime matrix.

## Acceptance

- Scheduled freshness reporting does not silently change production locks.
- Quality gates fail closed on provenance or contract drift.
- Results are consumable by the manuscript evidence register.
