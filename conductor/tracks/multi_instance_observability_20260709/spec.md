# Track: Multi-instance observability
Track ID: `multi_instance_observability_20260709`

## Goal

Doctor/backfill report/horizon per instance and jurisdiction; CI parity checks.

## Satisfies

`R-48`

## Dependencies

- `multi_instance_orchestration_20260709`
- `multi_instance_publish_20260709`

## Scope

- doctor instance filters
- coverage horizon per instance
- CI parity multi-dataset

## Out of scope

- Capture health internals (fyi-cli)
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
