# Track: Multi-instance orchestration
Track ID: `multi_instance_orchestration_20260709`

## Goal

Config registry; CLI --instance / env; plumb --base-url into seed/sync; relax manifest schema (source + instance_id); NZ default regression suite.

## Satisfies

`R-40`, `R-41`, `R-42`

## Dependencies

- none

## Scope

- instances registry module
- CLI --instance and FYI_ARCHIVE_BASE_URL
- manifest schema multi-source
- seed/sync pass --base-url to fyi-cli
- NZ regression tests

## Out of scope

- Capture/fetch logic (fyi-cli only)
- AU jurisdiction taxonomy (separate track)
- Live AU crawl
- Capture/fetch/WARC logic inside fyi-archive (belongs in fyi-cli)
- Write/submit operations against Alaveteli
- AI-training packaging of the archive

## Acceptance criteria

- [ ] Spec scope delivered with tests or evidence where applicable
- [ ] NZ default paths remain green (no regression)
- [ ] Rate limits / robots discipline documented for any live work
- [ ] Linked GitHub parent issue and sub-issues updated on completion

## Risks

- Live Alaveteli endpoints may present Cloudflare or rate-limit friction — smoke first, scale later
- Cross-instance data contamination — isolated paths and HF repos
