# English Alaveteli instance onboarding

Reusable checklist for a new English-language instance such as
`uk-wdtk`. This document prepares an isolated, read-only pilot; completing it
does not authorize a live crawl.

## 1. Source and operator contact

- [ ] Confirm the canonical public base URL and the instance operator's preferred
      contact channel.
- [ ] Send a concise notice describing the research purpose, read-only access,
      expected request volume, contactable User-Agent, retention, and takedown path.
- [ ] Record any published API, robots, crawl-delay, terms, or operator guidance.
- [ ] Stop if access requires login, bypassing controls, or ignoring a policy signal.

## 2. Technical registration

- [ ] Add an `ArchiveInstance` entry with a unique ID, locale, source URL, rate-limit
      bucket, and separate HF repository.
- [ ] Add instance-specific fixtures and a default-path regression test.
- [ ] Set an explicit capture base URL; keep any catalog URL override separate.
- [ ] Confirm manifests, state, ledgers, artifacts, and mirror targets cannot overlap
      an existing instance.

## 3. Gentle pilot

- [ ] Run only the deterministic dry-run first.
- [ ] Run a bounded live smoke only after the source contact/policy gate passes.
- [ ] Use the archive defaults: two seconds between requests, one worker, bounded
      request/runtime/disk caps, shared limiter, retries, and resumable ledger.
- [ ] Verify robots enforcement, User-Agent identity, Retry-After handling, and a
      retained provenance sidecar before expanding the cap.
- [ ] Stop on repeated 403/429/5xx responses, policy ambiguity, operator concern,
      or any evidence of unexpected load.

## 4. Evidence and promotion

- [ ] Retain the workflow URL, catalog/capture provenance, manifest checksum,
      request count, failure summary, and mirror verification report.
- [ ] Review the smoke evidence with the maintainer and source contact where needed.
- [ ] Keep the instance `experimental` until evidence supports promotion.
- [ ] Never claim full coverage from a smoke, capped, or fallback run.

See [`docs/ethics-and-compliance.md`](ethics-and-compliance.md) and the
[global onboarding template](instance-onboarding-global.md) for privacy and
locale considerations.
