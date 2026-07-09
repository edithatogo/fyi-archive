# Track: Multi-instance publish
Track ID: `multi_instance_publish_20260709`

## Goal

HF/Zenodo/OSF identity for au-rtk; draft-first; verification under AU paths; never write AU into NZ dataset.

## Satisfies

`R-46`, `R-22`

## Dependencies

- `multi_instance_orchestration_20260709`
- `au_nsw_historical_seed_20260709`

## Scope

- per-instance HF repo config
- draft-first AU publish
- mirror verification evidence
- dataset card AU

## Out of scope

- Mixing AU into fyi-archive-nz
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
