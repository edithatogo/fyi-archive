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
