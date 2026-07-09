# Ethics & compliance

## Posture

This archive performs **read-only** capture of public information from third-party
Alaveteli services (fyi.org.nz, righttoknow.org.au, whatdotheyknow.com,
myrighttoknow.org). We treat every source with care:

- **Public endpoints only.** No login, no write/submit, no use of any authenticated
  API. Alaveteli's read surface is public by design.
- **Rate-limited.** A token-bucket (~1 request/second with jitter by default) and
  bounded concurrency ensure sites are never hammered. Each instance has its own
  rate-limit bucket to prevent cross-site interference.
- **`robots.txt`-aware.** Disallowed paths are skipped; the file is re-fetched
  periodically.
- **Contactable identity.** Every request carries a descriptive `User-Agent`
  including a contact address, so site operators can reach us.
- **Trickle pace.** Multi-instance capture runs at a deliberately slow pace
  (1 request/second, 2 concurrent) to minimise impact on source sites.

## Not affiliated

This project is independent of and not endorsed by the operators of fyi.org.nz,
righttoknow.org.au, whatdotheyknow.com, myrighttoknow.org, the Alaveteli project,
or any public body. The archive is a point-in-time research copy; the live sites
remain the authoritative records.

## Purpose statement

This archive is built for **research, transparency, and public interest** purposes.
It is **not** collected for:

- **AI training or LLM development** — archived content is not used to train
  machine learning models.
- **Commercial purposes** — the archive is a non-commercial research project.
- **Surveillance or monitoring** — the archive preserves public records for
  historical and research access.

The primary use cases are:

- Preserving access to public information that may be lost or changed over time.
- Enabling academic research on freedom of information processes.
- Supporting journalism and public accountability.
- Providing a durable, citable record of government transparency.

## Legal

Archived content remains © its respective contributors / the Crown / the relevant
Alaveteli site. The archive redistributes already-published public material for
research and transparency under the copyright provisions documented in
[`copyright-and-licensing.md`](copyright-and-licensing.md). The **code** is MIT;
the **data** retains the source's rights status and is recorded per-item
(`license` + `attribution` fields). See `NOTICE.md`.

## Operational safety

- Hard caps on every historical-seed run: `--max-requests`, `--max-bytes`,
  `--max-runtime-minutes`, `--max-disk-gb`. The full-site crawl is date-windowed and
  fan-out, resumable from a ledger — never one monolithic job.
- All publishing is **draft-first**; production Zenodo DOI publishing is gated behind
  a protected environment and an explicit confirmation string.
- Each instance (NZ, AU, UK, IE) has independent rate-limit buckets and capture
  scheduling to prevent any single instance from impacting others.
