# Sigstore Signing Opt-In

Release artifacts are already covered by GitHub build-provenance attestations. Keyless
Sigstore signing with `cosign` is intentionally **off by default** until the archive
publication path is stable and the release process has been reviewed.

## When to enable

Enable keyless signing only after:

- `publish_archives.yml` exists and produces the final archive artifacts.
- The Zenodo production publish gate has been tested with a sandbox deposition.
- Maintainers agree that signed artifacts are part of the public release contract.

## Proposed workflow shape

The release job would need:

- `permissions: id-token: write` for OIDC.
- `cosign sign-blob --yes <artifact>` for each release artifact.
- Signature and certificate files uploaded beside each artifact.
- Verification instructions in `README.md` and release notes.

Example command shape:

```bash
cosign sign-blob --yes \
  --output-signature dist/fyi_archive.duckdb.sig \
  --output-certificate dist/fyi_archive.duckdb.pem \
  dist/fyi_archive.duckdb
```

Consumers would verify with:

```bash
cosign verify-blob \
  --certificate dist/fyi_archive.duckdb.pem \
  --signature dist/fyi_archive.duckdb.sig \
  --certificate-identity-regexp "https://github.com/edithatogo/fyi-archive/.github/workflows/.*" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  dist/fyi_archive.duckdb
```

This remains an improvement backlog item rather than active release behavior.
