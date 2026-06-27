# Ethics & compliance

## Posture

This archive performs **read-only** capture of public information from a third-party
service (`fyi.org.nz`). We treat the source with care:

- **Public endpoints only.** No login, no write/submit, no use of any authenticated
  API. Alaveteli's read surface is public by design.
- **Rate-limited.** A token-bucket (~1 request/second with jitter by default) and
  bounded concurrency ensure the site is never hammered.
- **`robots.txt`-aware.** Disallowed paths are skipped; the file is re-fetched
  periodically.
- **Contactable identity.** Every request carries a descriptive `User-Agent`
  including a contact address, so site operators can reach us.

## Not affiliated

This project is independent of and not endorsed by the operators of fyi.org.nz, the
Alaveteli project, or any NZ public body. The archive is a point-in-time research
copy; the live site remains the authoritative record.

## Legal

Archived content remains © its respective contributors / the Crown / fyi.org.nz. The
archive redistributes already-published public material for research and transparency
under the copyright provisions documented in
[`copyright-and-licensing.md`](copyright-and-licensing.md) (Copyright Act 1994; NZGOAL;
IPONZ). The **code** is MIT; the **data** retains the source's rights status and is
recorded per-item (`license` + `attribution` fields). See `NOTICE.md`.

## Operational safety

- Hard caps on every historical-seed run: `--max-requests`, `--max-bytes`,
  `--max-runtime-minutes`, `--max-disk-gb`. The full-site crawl is date-windowed and
  fan-out, resumable from a ledger — never one monolithic job.
- All publishing is **draft-first**; production Zenodo DOI publishing is gated behind
  a protected environment and an explicit confirmation string.
