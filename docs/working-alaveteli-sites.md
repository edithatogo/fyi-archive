# Working Alaveteli sites

The scheduled `Alaveteli working sites` workflow covers four non-NZ/non-AU
instances whose public authority catalogs were verified as downloadable:

| Instance | Country | Catalog |
| --- | --- | --- |
| `se-handlingar` | Sweden | `body/all-authorities.csv` |
| `ua-dostup` | Ukraine | `body/all-authorities.csv` |
| `uy-quesabes` | Uruguay | `body/all-authorities.csv` |
| `ge-askgov` | Georgia | `body/all-authorities.csv` |

Each scheduled run is sequential across sites and runs at 01:00 UTC, overnight
in all four countries. Manual dispatch defaults to a deterministic dry run;
manual live capture requires the explicit confirmation string. Live capture is
restricted to each country's local overnight hours, caps each site at five
requests, uses one in-flight request, and waits at least 60 seconds between
requests. A failed request is recorded and does not trigger an unbounded retry.

The catalog URL and capture base URL are separate inputs. Catalog discovery is
read-only and records catalog provenance alongside the site manifest. The
bounded ID queue is only a safety fallback when request-feed discovery is not
available; it is never expanded automatically.

For deployments whose live API is unavailable, the monthly `Alaveteli historical
indexes` workflow queries Internet Archive CDX in `url_index` mode only: one
record per archived URL. Its artifacts are historical evidence and do not imply
complete capture-version coverage or successful live capture. The manual-only
`Alaveteli historical all-captures export` workflow removes URL collapsing and
requires the `EXPORT_ALL_CAPTURE_METADATA` confirmation. It records every
reported timestamped CDX record or fails without producing a partial export;
it does not replay pages, publish, or create an empirical manifest.

Operator-supplied Atom/JSON exports can be imported with
`scripts/import_historical_sources.py`; the importer records input checksums,
instance identity, and source mode.
