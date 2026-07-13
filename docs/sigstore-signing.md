# Sigstore Signing Opt-In

Release artifacts are already covered by GitHub build-provenance attestations. An
additional keyless Sigstore path is available through
`.github/workflows/sign_release_artifacts.yml`, but remains **off by default**.

## When to enable

The opt-in workflow requires:

- an existing release tag;
- the `sigstore-production` protected environment;
- the exact confirmation string `sign-release-artifacts`; and
- `WORKFLOW_PAT` with permission to attach the generated bundles.

It currently signs and verifies the release's `provenance.json` and
`sbom.cdx.json` assets, then attaches the Sigstore bundles. Archive payload
signing remains a future extension once payloads are consistently attached to
GitHub releases.

## Workflow shape

The release job would need:

- `permissions: id-token: write` for OIDC, scoped to the signing job.
- `cosign sign-blob --yes --bundle <artifact>.sigstore.json <artifact>`.
- Bundles uploaded beside each signed release evidence asset.
- Verification instructions in `README.md` and release notes.

Example command shape:

```bash
cosign sign-blob --yes \
  --bundle dist/fyi_archive.duckdb.sigstore.json \
  dist/fyi_archive.duckdb
```

Consumers would verify with:

```bash
cosign verify-blob \
  --bundle dist/fyi_archive.duckdb.sigstore.json \
  --certificate-identity-regexp "https://github.com/edithatogo/fyi-archive/.github/workflows/.*" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  dist/fyi_archive.duckdb
```

The workflow remains opt-in rather than active release behavior.
