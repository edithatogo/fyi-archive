# Track: AU jurisdiction rollout controller
Track ID: `au_jurisdiction_rollout_controller_20260709`

## Goal

After NSW exit criteria: sequential VIC..OTHER; shared AU limiter; merge national AU manifest; controller issue state.

## Satisfies

`R-45`, `R-42`

## Dependencies

- `au_nsw_historical_seed_20260709`

## Scope

- jurisdiction order config
- GHA controller + issue state
- merge national manifest
- shared rate-limit name

## Out of scope

- Parallel full-rate multi-state crawl
- Non-AU instances
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
