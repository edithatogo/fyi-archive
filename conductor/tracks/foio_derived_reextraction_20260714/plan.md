# Plan: FOI-O derived re-extraction publication

## Phase 1: Contract and storage boundary

- [ ] Pin the source `fyi-archive-nz` revision and FOI-O extraction contract.
- [ ] Define and validate a versioned derived-manifest schema.
- [ ] Define separate local and Hugging Face paths or dataset identity for derived records.
- [ ] Add negative tests preventing raw-manifest replacement or field conflation.

## Phase 2: Publication and verification

- [ ] Accept `nlp-policy-nz` candidate outputs without embedding NLP logic here.
- [ ] Generate provenance, checksums, dataset-card disclosures, and a baseline-delta report.
- [ ] Add dry-run and round-trip tests for derived publication.
- [ ] Verify the remote derived manifest independently after publication.

## Phase 3: Human gates and closeout

- [ ] `[HUMAN]` Approve the dataset identity and publication target.
- [ ] `[HUMAN]` Approve any promotion from candidate to reviewed or gold status.
- [ ] Run repository quality gates and Conductor review.
- [ ] Archive the track only after local verification and remote evidence are recorded.
