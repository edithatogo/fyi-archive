# RIOPA field mapping adapter

`conformance/riopa/v1/fyi-archive-mapping.json` is the machine-readable,
language-neutral mapping from native fyi-archive archive, publication, and
research-object evidence to RIOPA v1 fields. It is additive: existing manifests,
provenance, mirror verification, and citation outputs remain the source evidence.

Each mapping is classified as:

- `exact`: the native value has the same meaning and representation;
- `approximate`: the value can seed the RIOPA field but needs additional
  validation or context;
- `extension-only`: valuable native evidence with no normative RIOPA field; or
- `unmapped`: no safe generic projection is currently defined.

The representative fixture is synthetic and makes no live-publication claim.
`adapter-report.json` embeds that complete native fixture, records canonical
SHA-256 digests, and adds projections without deleting or rewriting native
values. Regenerate it offline with:

```bash
uv run python scripts/build_riopa_adapter_report.py
```

Central conformance consumers can parse the three JSON files without importing
Python. Approximate values must not be treated as exact conformance, and
extension-only or unmapped evidence remains available under
`native_evidence_fixture`.
