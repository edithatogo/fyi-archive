# Track: AU RTK ethics and metadata
Track ID: `au_rtk_ethics_metadata_20260709`

## Goal

AU ethics, copyright sketch, policy-research purpose (not AI training), Content-Signal/robots note, takedown contact.

## Satisfies

`R-43`

## Dependencies

- `multi_instance_orchestration_20260709`

## Scope

- docs/ethics updates
- AU copyright note
- dataset card purpose language
- Content-Signal documentation

## Out of scope

- Legal advice
- Capture implementation
- Capture/fetch/WARC logic inside fyi-archive (belongs in fyi-cli)
- Write/submit operations against Alaveteli
- AI-training packaging of the archive

## Acceptance criteria

- [x] Spec scope delivered with tests or evidence where applicable
- [x] NZ default paths remain green (no regression)
- [x] Rate limits / robots discipline documented for any live work
- [x] Linked GitHub parent issue and sub-issues updated on completion

## Risks

- Live Alaveteli endpoints may present Cloudflare or rate-limit friction — smoke first, scale later
- Cross-instance data contamination — isolated paths and HF repos
