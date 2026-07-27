# Source and transformation provenance

## Principles

- Raw captures and third-party indexes remain immutable inputs.
- Derived inventories never replace WARC/WACZ records.
- Every transformation has a stable identifier, documented rules, input
  hashes, and an output payload hash.
- Normalization is loss-minimizing and does not infer country, jurisdiction,
  legal status, or completeness.
- Synthetic, test, private, and rights-restricted records are classified
  explicitly rather than silently dropped.

## Source graph transformation

`normalize-archive-sources-v1` joins four declared inputs:

- the Alaveteli instance registry;
- the additional FOI site registry;
- the jurisdiction completion ledger; and
- the preservation-source overlay.

It requires every site and jurisdiction to resolve exactly once. It copies
source states into a normalized graph and labels unverified preservation
sources `not_probed`.

## Completeness transformation

`reconcile-public-archive-completeness-v1`:

1. Reads JSON, JSONL, or CDX JSON URL inventories.
2. Lowercases scheme and host, removes fragments and non-root trailing slashes,
   and preserves path and query semantics.
3. Excludes rows explicitly marked synthetic or identified by documented
   dry-run/test state and title rules.
4. Deduplicates normalized URLs.
5. Computes set-based matches and gaps for each independent channel.
6. Emits input SHA-256 values, duplicate and exclusion counts, and every
   missing or unexpected URL.

The transformation never treats an empty archive response as proof of an empty
population and never converts a configured source into a verified source.
