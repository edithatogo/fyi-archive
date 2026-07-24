# Plan: FOI-O derived re-extraction publication

Consumer gate: `tests/test_foio_extraction_contract.py` validates the pinned
FOI-O extraction-contract shape. The test is a structural gate; publication
still requires real source and Hugging Face digests.

## Phase 1: Contract and storage boundary

- [x] Pin the source `fyi-archive-nz` revision and FOI-O extraction contract.
- [x] Define and validate a versioned derived-manifest schema.
- [x] Define separate local and Hugging Face paths or dataset identity for derived records.
- [x] Add negative tests preventing raw-manifest replacement or field conflation.

## Phase 2: Publication and verification

- [x] Accept `nlp-policy-nz` candidate outputs without embedding NLP logic here.
- [x] Generate provenance, checksums, dataset-card disclosures, and a baseline-delta report.
- [x] Add dry-run and round-trip tests for derived publication.
- [ ] Verify the remote derived manifest independently after publication.

## Phase 3: Human gates and closeout

- [ ] `[HUMAN]` Approve the dataset identity and publication target.
- [ ] `[HUMAN]` Approve any promotion from candidate to reviewed or gold status.
- [x] Run repository quality gates and Conductor review (289 passed, 1 skipped;
  90.70% coverage and all mandatory static/contract checks passed on 2026-07-24).
- [ ] Archive the track only after local verification and remote evidence are recorded.
