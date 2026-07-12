# External source evidence

Checked 2026-07-12. These are candidate official datasets for the structured
import adapters, not claims that they are exports of a registered Alaveteli
instance:

- [FOIA.gov](https://www.foia.gov/) exposes a FOIA dataset download and is an
  official US source.
- [APHA FOI/EIR requests 2015](https://www.data.gov.uk/dataset/b4ad8745-e329-47df-ab34-722478dc97ea/apha-foi-eir-information-requests-2015)
  is an official UK open-data dataset containing request-level fields.
- [Data.gov.au FOI statistics](https://data.gov.au/data/dataset/freedom-of-information-statistics)
  is an official Australian statistics dataset, but is aggregate rather than
  request-level and is therefore not imported as request records.

No verified request-level export URL was found for the 15 historical-only
Alaveteli deployments in this pass. Operators can import a downloaded source
with `scripts/import_historical_sources.py`; the adapter records the local
file path, modification-time retrieval value, SHA-256, and normalized records.

The bounded live probes against `quesabes.org` on 2026-07-12 returned
non-JSON responses: HTTP 200 HTML for `output=json` and `output=atom` in the
first check, followed by HTTP 500 with a one-byte non-JSON body in the second
check. It is not currently compatible with fyi-cli's JSON feed contract.
`scripts/probe_alaveteli_feeds.py` now automates this one-request-per-instance
assessment with a 10-second default delay and records response status,
checksum, and content type.
