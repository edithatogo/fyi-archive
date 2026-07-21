# Maximal quality profile

The archive uses a locked Python 3.12 production environment. Python 3.13 and
3.14 run as non-blocking canaries until all native dependencies and the
cross-repository contract matrix are verified.

Stable Ruff lint and formatting, ty, tests, coverage, schema/provenance/digest
checks, workflow syntax, SBOM generation, dependency hygiene, and security
checks are release gates. Ruff preview is a separate advisory lane. Strict
basedpyright runs over source, tests, and scripts as a baseline; its current
baseline is 974 findings on 2026-07-14 and must trend to zero before it becomes
blocking.

Pydantic v2 and JSON Schema remain the payload boundaries. PydanticAI, DSPy,
and other LLM orchestration packages are not runtime dependencies and may only
appear in explicitly isolated adapters or experiments.

Freshness reports inspect the committed lockfile and may open upgrade issues;
they never rewrite production dependencies without review.
