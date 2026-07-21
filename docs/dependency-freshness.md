# Dependency freshness register

Snapshot checked 2026-07-14 against the committed `uv.lock`.

| Dependency | Locked | Latest observed | Decision |
|---|---:|---:|---|
| pydantic | 2.13.4 | 2.13.4 | Current |
| pydantic-settings | 2.14.2 | 2.14.2 | Current |
| ruff | 0.15.20 | 0.15.21 | Patch review candidate |
| ty | 0.0.55 | 0.0.59 | Compatibility review candidate |
| pytest | 9.1.1 | 9.1.1 | Current |
| polars | 1.42.0 | 1.42.1 | Patch review candidate |
| pyarrow | 24.0.0 | 25.0.0 | Compatibility review candidate |

The lockfile remains authoritative. Automated freshness reporting must not
silently update it.

## Review note

The 2026-07-14 `uv lock` run reported `pandas==3.0.4` as yanked because of
reported segmentation faults. It remains in the resolved graph through an
optional development path and requires explicit dependency review before a
release; this track does not silently replace it.
