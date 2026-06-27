# Learning Log

Short, dated entries capturing non-obvious findings during work.

## 2026-06-27
- **fyi.org.nz API shape:** reads need no auth; append `.json` to most URLs;
  `/request/{id}.json` 302-redirects to `/request/{url_title}.json` (follow
  redirects). Bulk enumeration is via advanced-search Atom feeds + their `.json`
  equivalents — there is no `list.json`. → Drives the `bulk-site-enumeration`
  capability in `fyi-cli`.
- **fyi-cli cannot enumerate the site today:** it only fetches a single request by ID
  and reads feeds. The full-site archive therefore requires *new* `fyi-cli`
  capabilities (enumeration, WARC/WACZ capture, diff, health), not a reimplementation
  inside `fyi-archive`.
- **Token availability:** `HF_TOKEN`, `OSF_TOKEN`(+user/pass), `ZENODO_TOKEN`,
  `ZENODO_SANDBOX_TOKEN`, `GITHUB_TOKEN` present locally in the workspace `.env`.
  `osfclient`/`zenodo-client` not installed → use raw `requests` (matches siblings).
- **Conductor path quirk:** `fyi-cli` uses `.conductor/` (leading dot); this repo and
  the corpus siblings use `conductor/`.
