# Maximal quality profile

Audit the archive as an evidence-producing pipeline: lockfile freshness,
strict typing, schema/property/mutation tests, provenance, digest checks, and
cross-repository release compatibility.

## Acceptance

- Scheduled freshness reporting does not silently change production locks.
- Quality gates fail closed on provenance or contract drift.
- Results are consumable by the manuscript evidence register.
