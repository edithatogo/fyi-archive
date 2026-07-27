# Global archive completeness and redundancy

## What “complete” means

Completeness is measured against an enumerated public URL inventory, not a
guessed numeric ID ceiling. Private, hidden, embargoed, or redacted records are
never copied into public archives. When an operator can confirm that an
excluded record exists, the public evidence may contain an opaque tombstone,
but not the excluded content.

The project reports independent measures:

1. **Primary completeness** — enumerated public URLs preserved by the
   content-addressed primary capture.
2. **Internet Archive completeness** — enumerated public URLs present in a
   complete CDX inventory and replay-checked where practical.
3. **Minimum preservation** — enumerated URLs present in at least one
   preservation channel.
4. **Dual primary/Wayback preservation** — URLs present in both the primary
   capture and Internet Archive evidence.
5. **Independent redundancy** — URLs present in two or more independent
   preservation channels.

No successful smoke run, capped query, first page, planning horizon, or empty
response proves completeness.

## Source graph

`configs/archive_source_graph.json` maps all 29 site identities to all 42
jurisdiction targets. It also declares Internet Archive for every site and
records candidate independent sources such as national web archives, Common
Crawl, and Arquivo.pt.

Build the normalized graph:

```console
uv run python scripts/build_archive_source_graph.py --check --output dist/archive-source-graph.json
```

The output records the SHA-256 of every input and a deterministic payload hash.
Candidate sources remain `not_probed` until source-specific evidence is
captured; configuration never becomes an availability claim.

## Per-site reconciliation

```console
uv run python scripts/reconcile_archive_completeness.py \
  --site-id nz-fyi \
  --enumerated evidence/nz/public-urls.jsonl \
  --primary evidence/nz/primary-capture.jsonl \
  --internet-archive evidence/nz/internet-archive-cdx.json \
  --secondary nz-web-archive=evidence/nz/national-library.jsonl \
  --output evidence/nz/completeness.json
```

The report records input hashes, URL normalization, duplicates removed,
synthetic rows excluded, missing URLs, unexpected URLs, and channel-specific
percentages.

## New Zealand closure

The NZ public denominator must be obtained from an operator export or a fully
paginated Alaveteli enumeration. The published dataset must first remove or
separate `dry-run` records. Each remaining request URL, event history, and
public attachment is captured to WARC/WACZ, reconciled against the denominator,
queried in the Internet Archive, and checked against the New Zealand Web
Archive where access permits.

Two consecutive incremental enumerations with no unexplained gaps establish a
closure checkpoint. Daily sync then maintains, rather than permanently
guarantees, 100% public coverage.

## Autonomous operation and safety

Public, read-only discovery and capture proceed automatically when registry,
rate-limit, robots/terms, rights, privacy, and integrity checks pass.
Interactive confirmation is not an operational dependency. Missing evidence,
credentials, rights clearance, or publication configuration causes the
affected operation to fail closed and leaves a machine-readable blocker.

Internet Archive CDX discovery does not itself submit a missing page to the
Wayback Machine. Full-site prospective preservation should use an agreed
Archive-It or equivalent crawl where available; single-page submission is a
gap-filling mechanism, not a completeness strategy.
