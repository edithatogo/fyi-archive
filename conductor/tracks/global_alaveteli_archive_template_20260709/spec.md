# Track: Global Alaveteli archive template
Track ID: `global_alaveteli_archive_template_20260709`

## Goal

i18n instance onboarding post-English; locale/GDPR notes; depends fyi-cli i18n.

## Satisfies

`R-50`

## Dependencies

- `english_alaveteli_archive_template_20260709`

## Scope

- i18n onboarding checklist
- GDPR/PII notes
- instance config template

## Out of scope

- Live non-English full archives (later)
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
