# Australian FOI Corpus Readiness

The versioned sampling contract is
[`configs/au/corpus_sampling_frame.json`](../configs/au/corpus_sampling_frame.json).
It defines separate Commonwealth (`FEDERAL`) and New South Wales (`NSW`)
strata, explicit unknown categories, and
the outcome, agency, correspondence, and attachment dimensions to report.

The approved AU-NSW frame is restricted-local:

- `capture_authorized=true` for the pinned 179-record NSW frame;
- `publication_authorized=false`;
- the capture window is the approved full pinned frame;
- source terms, takedown, sensitive-data review, and permitted-use records are
  mandatory;
- missing outcome classes are reported and never filled with inferred or
  synthetic records.

Validate the contract locally:

```text
uv run fyi-archive process validate-au-sampling-frame
```

This contract authorizes restricted-local capture of the approved NSW frame. It
does not approve data publication, redistribution, training, or establish
jurisdictional completeness.
