# FOI-O Derived Layer

FOI-O/NLP outputs are a separately versioned, candidate-only layer. They never
replace the raw request records, WARC/WACZ captures, or their manifests.

Validate an upstream extraction declaration before staging it:

```text
uv run fyi-archive process validate-derived \
  --manifest path/to/foi-o-derived-manifest.json
```

The validator requires the `foi-o-extraction-contract/0.1.0` contract, an
immutable source revision and SHA-256, pinned ontology/profile/codebook
digests, and extraction-run and pipeline provenance. `candidate_status` must
remain `candidate`; candidate annotations are not certified legal findings or
gold labels.

The machine-readable contract is
[`schemas/foi-o-derived-manifest.schema.json`](../schemas/foi-o-derived-manifest.schema.json).

## Local package and round-trip verification

Candidate outputs can be staged without publishing them:

```text
uv run fyi-archive process package-derived \
  --manifest path/to/foi-o-derived-manifest.json \
  --candidates path/to/candidates.ndjson \
  --baseline path/to/prior-candidates.ndjson \
  --output-dir dist/foi-o-derived

uv run fyi-archive process verify-derived-bundle \
  --output-dir dist/foi-o-derived
```

The package records SHA-256 digests, byte sizes, candidate counts, and
candidate-level additions, removals, and changes. It always writes
`publication_status=not_published`; packaging is not upload, verification,
review, or publication permission.

Every NDJSON row requires a stable `candidate_id`. Raw message/request bodies,
OCR text, and attachment bytes are rejected. Dataset descriptions must retain
the following disclosure:

> FOI-O/NLP outputs are inferred candidates for research evaluation. They are
> not gold labels, certified legal findings, legal advice, or replacements for
> immutable archive evidence.
