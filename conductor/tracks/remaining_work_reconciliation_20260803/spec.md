# Specification

Reconcile the repository's remaining work without deleting datasets, broadening
credentials, or dispatching unbounded retries. The track owns the closure ledger
for the open Wayback partition trial, scheduled fail-closed sites, Hugging Face
metadata correction, and optional dedicated GitHub Project credentials.

## In scope

1. Keep Wayback acquisition resumable and fail-closed; run at most one bounded,
   explicitly named partition trial and retain its manifests, retrieval records,
   checkpoints, configuration identity, fingerprints, and verifier output.
2. Keep CA, DE, UK, and any other incomplete sites on their existing weekly
   schedule unless a human explicitly requests a bounded targeted run.
3. Preserve the canonical Hugging Face dataset and attempt metadata-only card
   correction only when provider authorization permits it.
4. Record project-sync success via fallback credentials while keeping dedicated
   least-privilege credential hardening optional and explicit.

## Out of scope

Dataset deletion or rewriting, automatic retry loops, credential values, release
publication, and claiming percentage coverage without a defensible denominator.
