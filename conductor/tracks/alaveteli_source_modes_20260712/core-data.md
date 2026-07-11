# Historical core-data enrichment

`alaveteli_historical_core.yml` reads Internet Archive replay pages only. It
extracts conservative core fields: request URL/key, title, authority, state,
first-seen date, last-updated date, archive replay URL, archive timestamp,
archive digest, content checksum, and extraction status.

Blank fields mean the archived page did not expose a value. Fetch failures are
retained as records with a bounded diagnostic; no value is inferred from the
request URL or from a live origin-site request.
