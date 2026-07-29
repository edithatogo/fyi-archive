# Hugging Face archive catalog

The public
[fyi-archive collection](https://huggingface.co/collections/edithatogo/fyi-archive-global-public-information-request-archives-6a6946d45c8cc5852a1d62d4)
groups the 23 independently scoped dataset repositories registered in
`src/fyi_archive/instances.py`.

## Live setup receipt

On 2026-07-29, the authenticated `edithatogo` namespace was reconciled against the
instance registry:

- one dedicated public collection, with `theme=blue`;
- exactly 23 dataset members, ordered as supported, experimental, then
  historical-only;
- one instance-specific `README.md` in every repository;
- language metadata derived from the registered locale;
- text-retrieval, no-annotation, and external-source metadata;
- `license: other` for all archive datasets, because the source records do not inherit
  the orchestration code's MIT licence;
- operational status, canonical source, acquisition modes, intended use, rights,
  limitations, and citation metadata on every card.

The first idempotence check reported all 23 cards as unchanged after publication. Live
repository inspection confirmed 23/23 README files, 23/23 language tags, and 23/23
`license:other` tags.

## Viewer boundary

Only a repository containing a verified tabular artifact should advertise a Hub
Dataset Viewer configuration. The supported NZ repository currently points its
`requests` split at `manifests/latest_manifest.parquet`. Empty experimental and
historical shells deliberately omit `configs`: inventing a split for absent data would
turn a publication gap into a misleading viewer error.

The NZ viewer is valid and searchable with 33,217 rows, 13 columns, and one Parquet
shard. Several optional fields are currently null-only and are documented as
unavailable rather than inferred. The 22 remaining repositories require verified
derived Parquet before Viewer, search, statistics, or generated Croissant can be
enabled.

When a non-NZ instance publishes a verified manifest, `hf_sync.yml` renders that
instance's card before upload. It must not reuse the NZ card or claim a record count
before the remote manifest verification succeeds.

## Reconciliation

Preview the deterministic plan:

```bash
uv run python scripts/ensure_huggingface_archive_catalog.py
```

Apply it with the active Hugging Face token:

```bash
uv run python scripts/ensure_huggingface_archive_catalog.py --apply
```

The operation is idempotent. It creates missing repository shells, updates only cards
whose bytes differ, adds missing collection members, and restores the deterministic
collection order. Authentication failures and network errors fail closed.
