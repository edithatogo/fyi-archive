# Track: GitHub project multi-jurisdiction issues
Track ID: `github_project_multi_jurisdiction_20260709`

## Goal

Parent/sub-issues for multi-jurisdiction tracks; labels; project board; RIOPA sync verification.

## Satisfies

`R-47`

## Dependencies

- none

## Scope

- parent issues per track
- sub-issues
- labels
- project + RIOPA sync

## Out of scope

- Nested GitHub projects (unsupported)
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
