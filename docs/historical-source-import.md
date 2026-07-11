# Historical source import

The repository can combine downloaded historical indexes without contacting the
live source:

```powershell
uv run python scripts/import_historical_sources.py `
  --morph-csv path/to/morph.csv `
  --internet-archive-cdx path/to/cdx.json `
  --output manifests/historical_source_index.json
```

Morph CSV rows and Internet Archive CDX rows are retained as evidence inputs,
not converted into live-capture records. The output records each input path,
local retrieval time, SHA-256 checksum, source type, and row count. Duplicate
request URLs are represented once, with the first source record retained.

This process does not access Right to Know, does not use a proxy, and does not
claim that a page or attachment was captured. A later capture step must verify
each URL through a permitted read-only route before it can enter a WARC/WACZ
manifest.

## GitHub Actions

The `Historical source indexes` workflow refreshes both inputs weekly and can
also be started manually. It requires the repository secret `MORPH_API_KEY`
because Morph's public data API requires an API key. The workflow has only
`contents: read`, uses bounded requests, and retains the raw inputs and merged
index as a 90-day artifact.
