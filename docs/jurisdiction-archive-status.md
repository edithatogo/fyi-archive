# Jurisdiction Archive Completion Status

The machine-readable programme ledger is
[`configs/jurisdiction_archive_targets.json`](../configs/jurisdiction_archive_targets.json).
It covers all 42 archive targets named by FOI-O programme issues 81–86.

Each target must be exactly one of:

- `archived`, with an immutable manifest digest and capture revision;
- `blocked`, with an explicit blocker and evidence state; or
- `unsupported`, with an explicit adapter/capability gap.

The initial ledger is conservative: no target is marked archived merely
because a smoke capture, platform listing, or neighbouring jurisdiction exists.
The Australian pilot remains approval-gated, Sweden records its HTTP 403
boundary, and non-Alaveteli targets remain unsupported until a bounded adapter
is proven. Publication is globally disabled in this ledger.

Validate it locally:

```text
uv run fyi-archive process validate-jurisdiction-targets
```

Promoting a target to `archived` requires target-specific rights review,
privacy checks, capture revision, manifest SHA-256, and replay evidence.
