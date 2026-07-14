# Specification: FOI-O derived re-extraction publication

## Objective

Extend the storage-first archive with an explicitly separate derived-publication
lane for candidate NER/NLP annotations produced by `nlp-policy-nz` from a pinned
`fyi-archive-nz` revision and a pinned FOI-O contract.

## Boundaries

- Raw manifests, WARC/WACZ resources, and their revisions remain immutable.
- `fyi-cli` continues to own all network capture.
- `nlp-policy-nz` owns extraction logic and model execution.
- `fyi-archive` validates, packages, publishes, and verifies the derived layer.
- Alaveteli remains an upstream data/workflow source, not a code dependency.
- `fe-reader` is not part of this track.

## Required derived manifest fields

- source dataset repository, revision, record identifier, and content digest;
- extraction run identifier and timestamp;
- FOI-O ontology, schema, and codebook versions;
- NLP pipeline and model identifiers plus parameters;
- evidence spans, confidence, candidate status, and review status;
- supersedes/superseded-by links for repeat extractions.

## Acceptance criteria

- Derived outputs cannot overwrite or masquerade as raw archive fields.
- Publication is reproducible from pinned source and contract revisions.
- Hugging Face verification covers derived files and their manifest digests.
- A baseline-delta report compares the new extraction with the initial output.
- Dataset cards distinguish observed archive data from inferred candidates and
  prohibit treating candidates as certified legal findings or gold labels.
