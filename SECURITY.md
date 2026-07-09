# Security Policy

## Reporting a vulnerability

Please report security issues privately. Do **not** open a public issue.

- Email: `edithatogo@users.noreply.github.com` (preferably PGP-encrypted)
- Or use [GitHub's private vulnerability reporting](https://github.com/edithatogo/fyi-archive/security/advisories/new)

Acknowledge within 72 hours. Coordinated disclosure after a fix is released.

## Scope

This repository (`fyi-archive`) is the **orchestration + distribution** layer. It
contains no network-fetching logic of its own; all capture is delegated to
[`fyi-cli`](https://github.com/edithatogo/fyi-cli). Mirror publishing uses
`HF_TOKEN`, `ZENODO_TOKEN`, and `OSF_TOKEN`.

## Secret hygiene

- No secrets are committed. `.env` is gitignored; `.env.example` documents the
  expected variables.
- GitHub Actions secrets are the source of truth in CI. Protected environments gate
  production Zenodo publishing (`environment: zenodo-production`).
- All publish steps are **draft-first** by default; production publication requires an
  explicit confirmation string and a protected environment.

## Supply chain

- `uv.lock` is committed; CI installs with `uv sync --frozen`.
- CycloneDX SBOM is generated per release and attached to the GitHub Release and the
  Zenodo deposition.
- Release artifacts receive build-provenance attestations
  (`actions/attest-build-provenance@v4`).
- OpenSSF Scorecard and CodeQL run continuously; `zizmor` audits workflow security.
- CodeQL and Scorecard workflows finish with the org shared
  `code-scanning-gate` action (pinned to a commit SHA on `edithatogo/.github`)
  so open **high** / **critical** code-scanning alerts fail the job.
