# Australian FOI Corpus Readiness

The versioned sampling contract is
[`configs/au/corpus_sampling_frame.json`](../configs/au/corpus_sampling_frame.json).
It defines separate Commonwealth (`FEDERAL`) and New South Wales (`NSW`)
strata, explicit unknown categories, a maximum of 25 requests per stratum, and
the outcome, agency, correspondence, and attachment dimensions to report.

The frame is deliberately fail-closed:

- `capture_authorized=false`;
- `publication_authorized=false`;
- the capture window remains `pending_human_approval`;
- source terms, takedown, sensitive-data review, and permitted-use records are
  mandatory;
- missing outcome classes are reported and never filled with inferred or
  synthetic records.

Validate the contract locally:

```text
uv run fyi-archive process validate-au-sampling-frame
```

This contract prepares a bounded pilot. It does not authorize a live `fyi-cli`
run, dispatch a workflow, approve data publication, or establish jurisdictional
completeness.
