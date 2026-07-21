# Australian FOI corpus readiness

## Objective

Turn the existing AU multi-instance and dry-run infrastructure into pinned,
jurisdiction-stratified public example corpora suitable for FOI-O profile
development and evaluation without weakening live-capture or rights gates.

## Requirements

- Keep `fyi-cli` as the only capture implementation.
- Preserve raw RightToKnow/Alaveteli states, correspondence, attachments,
  timestamps, WARC/WACZ evidence, provenance, and content digests.
- Isolate Commonwealth, NSW, ACT, Queensland, Victoria, Western Australia,
  South Australia, Tasmania, and Northern Territory strata.
- Begin with operator-approved, capped Commonwealth and NSW samples.
- Record coverage across access, partial access, refusal, transfer, extension,
  fees, invalidity, information-not-held, and review where available.
- Publish raw and derived layers separately; NLP candidates cannot alter raw records.
- Document source terms, takedown route, sensitive-data handling, and permitted
  policy-research uses for every published sample.

## Acceptance criteria

- Each released sample has a pinned manifest, source revision, digests, rights
  record, jurisdiction tag, and selection rationale.
- Commonwealth and NSW pilot samples support reproducible FOI-O evaluation.
- Missing outcome classes and source limitations are reported rather than filled
  with synthetic or inferred records.
- Full live collection remains behind explicit operator approval.

## Out of scope

- legal interpretation;
- AI-training claims;
- direct NLP implementation;
- direct changes to upstream Alaveteli.
