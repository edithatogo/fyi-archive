# Track: AU jurisdiction taxonomy
Track ID: `au_jurisdiction_taxonomy_20260709`

## Goal

Body-tag to jurisdiction map; committed rules + fixtures; authorities manifest with jurisdiction field.

## Satisfies

`R-44`

## Dependencies

- `multi_instance_orchestration_20260709`

## Scope

- jurisdiction rules JSON
- fixtures from RTK tags
- mapping helpers + tests
- authorities_au schema

## Out of scope

- HTML scraping in archive (use fyi-cli bodies)
- Live full crawl
- Capture/fetch/WARC logic inside fyi-archive (belongs in fyi-cli)
- Write/submit operations against Alaveteli
- AI-training packaging of the archive

## Acceptance criteria

- [x] Spec scope delivered with tests or evidence where applicable
- [x] NZ default paths remain green (no regression)
- [x] Rate limits / robots discipline documented for any live work
- [~] Linked GitHub parent issue and sub-issues updated; live body enumeration remains blocked on #84

## Risks

- Live Alaveteli endpoints may present Cloudflare or rate-limit friction — smoke first, scale later
- Cross-instance data contamination — isolated paths and HF repos
