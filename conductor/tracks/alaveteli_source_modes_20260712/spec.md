# Alaveteli source modes

Track ID: `alaveteli_source_modes_20260712`

## Goal

Expand coverage beyond currently reachable live APIs using the existing fyi-cli
feed contract, local feed imports, and Internet Archive indexes without adding
traffic to origin sites.

## Source modes

- `live_api`: fyi-cli request capture and discovery.
- `atom_feed`: fyi-cli search-feed discovery or an operator-supplied Atom export.
- `authority_catalog`: public authority CSV catalog.
- `internet_archive`: CDX/WARC-derived historical evidence.
- `official_dataset`: future regulator/open-data imports.
- `operator_export`: future operator-provided dump with checksum validation.

## Safety

Historical index refreshes contact Internet Archive only. Live feed/capture
continues to use fyi-cli robots checks, shared rate limiting, bounded retries,
and country-local overnight windows.
