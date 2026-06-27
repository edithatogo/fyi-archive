# Product Guidelines

## Tone

Technical, precise, low-hype. "Bleeding-edge" describes tooling choices, not marketing.

## Provenance discipline

- Every release artifact carries build-provenance attestation and a `provenance.json`
  (source commit, fetch window, lockfile hash, runner env, WACZ hashes).
- Manifests are hash-evidenced; the HF mirror is re-downloaded and SHA-256 verified on
  every sync.

## Politeness

- One descriptive, contactable `User-Agent` for all outbound traffic.
- `robots.txt` respected; rate-limited (~1 req/s + jitter); bounded concurrency.
- Hard run caps on the historical crawl.

## Distribution clarity

- Hugging Face = live, content-revised dataset.
- Zenodo = annual, immutable DOI snapshot (draft-first, gated).
- OSF = project + components mirror.
- GitHub = code + releases + SBOM + provenance.

## What this repo does *not* do

- Fetch from the network (that's `fyi-cli`).
- Analyse, OCR, or normalise content (phase 1 non-goal).
- Serve an API or search index over the archive.
