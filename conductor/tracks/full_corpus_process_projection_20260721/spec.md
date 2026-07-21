# Specification: Full-corpus process projection and continuation

The archive consumes the versioned public-safe process-event stream emitted by
`fyi-cli` and materializes separate process-mining resources. Faithful WARC/WACZ
and raw request manifests remain the source evidence and are not replaced.

## Acceptance

- Contract version `1.0.0` is validated before output is written.
- Events retain source ordering and deterministic case projections.
- Events, cases, attachment metadata, and snapshot revisions are separate Parquet resources.
- Coverage, dataset metadata, and SHA-256 checksums are emitted.
- A checksum verification command fails closed before publication.
