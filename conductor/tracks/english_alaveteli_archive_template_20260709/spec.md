# Track: English Alaveteli archive template
Track ID: `english_alaveteli_archive_template_20260709`

## Goal

Reusable instance onboarding checklist post-AU; first candidate uk-wdtk.

## Satisfies

`R-49`

## Dependencies

- `au_jurisdiction_rollout_controller_20260709`

## Scope

- onboarding checklist
- rate-limit/ethics template
- issue form template

## Out of scope

- Full UK historical seed (later)
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
