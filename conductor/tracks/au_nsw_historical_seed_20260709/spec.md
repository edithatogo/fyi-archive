# Track: AU NSW historical seed
Track ID: `au_nsw_historical_seed_20260709`

## Goal

NSW-only discover to seed to manifest to capped smoke; isolated paths; parameterised workflows; default rate limits.

## Satisfies

`R-44`, `R-21`, `R-42`

## Dependencies

- `multi_instance_orchestration_20260709`
- `au_jurisdiction_taxonomy_20260709`
- `au_rtk_ethics_metadata_20260709`

## Scope

- NSW body queue
- isolated data/au-rtk/nsw paths
- workflow inputs instance+jurisdiction
- capped smoke + evidence

## Out of scope

- Other states
- Unlimited concurrency
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
