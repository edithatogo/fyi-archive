"""Hugging Face dataset-card metadata for registered archive instances."""

from __future__ import annotations

from fyi_archive.instances import ArchiveInstance

_LANGUAGE_NAMES = {
    "cs": "Czech",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "hr": "Croatian",
    "hu": "Hungarian",
    "ka": "Georgian",
    "nl": "Dutch",
    "ro": "Romanian",
    "sq": "Albanian",
    "sv": "Swedish",
    "uk": "Ukrainian",
}


def language_code(instance: ArchiveInstance) -> str:
    """Return the Hub language code derived from an instance locale."""
    return instance.locale.split("-", 1)[0].lower()


def collection_note(instance: ArchiveInstance) -> str:
    """Return a concise collection note for one dataset."""
    return (
        f"{instance.country} | {instance.status} | read-only archive of "
        f"{instance.capture_base_url()}."
    )


def render_instance_card(instance: ArchiveInstance) -> str:
    """Render a truthful card for a live, experimental, or historical archive shell."""
    language = language_code(instance)
    language_name = _LANGUAGE_NAMES.get(language, language)
    modes = "\n".join(f"- `{mode}`" for mode in instance.source_modes)
    status_text = {
        "supported": (
            "This is the supported production archive. Published snapshot metadata below is "
            "generated only after the remote manifest has been verified."
        ),
        "experimental": (
            "This repository is an experimental, independently scoped archive. A repository "
            "shell or dataset card does not imply that collection is complete or currently active."
        ),
        "historical-only": (
            "This repository is reserved for historical recovery. It is fail-closed: the card "
            "does not claim records, completeness, or live-API coverage until verified artifacts "
            "are published."
        ),
    }[instance.status]
    return f"""---
pretty_name: "{instance.title}"
license: other
language:
  - {language}
task_categories:
  - text-retrieval
annotations_creators:
  - no-annotation
source_datasets:
  - other
tags:
  - public-information
  - freedom-of-information
  - government-transparency
  - alaveteli
  - web-archive
  - warc
  - wacz
  - archival
  - jurisdiction-{instance.country.lower()}
---

# {instance.title}

Read-only public-information request archive for
**[{instance.capture_base_url()}]({instance.source})** ({instance.country}; {language_name}).
This dataset belongs to the dedicated `fyi-archive` collection.

## Publication status

- Instance id: `{instance.id}`
- Operational status: **{instance.status}**
- Canonical source: `{instance.source}`
- Dataset repository: `{instance.hf_repo_id}`

{status_text}

## Provenance and acquisition modes

The orchestration source is
[`edithatogo/fyi-archive`](https://github.com/edithatogo/fyi-archive). Capture is
read-only, rate-limited, independently checkpointed per site, and performed through
publicly available source interfaces and archival evidence. Configured source modes:

{modes}

## Intended use

Public-interest and policy research, journalism, reproducible historical preservation,
and transparency analysis. This archive is not a certified legal record, legal advice,
or a substitute for the upstream site.

## Data availability and loading

The repository card is always published before archive payloads. A Dataset Viewer
configuration is added only when a verified Parquet manifest exists. Until then, inspect
the repository without assuming a split:

```python
from huggingface_hub import HfApi

files = HfApi().list_repo_files("{instance.hf_repo_id}", repo_type="dataset")
print(files)
```

After `manifests/latest_manifest.parquet` is published and verified, it can be queried
with DuckDB or loaded explicitly as Parquet. The canonical manifest contract is
[`schemas/manifest.schema.json`](https://github.com/edithatogo/fyi-archive/blob/main/schemas/manifest.schema.json);
source-specific unavailable values remain null rather than being inferred.

## Rights, privacy, and limitations

Public availability does not create a blanket reuse licence. Archived records retain
their source rights, attribution, privacy, and takedown constraints; the repository
code alone is MIT-licensed. Coverage is point-in-time and may be incomplete. No
percentage coverage is claimed without a defensible source denominator. See the
[copyright](https://github.com/edithatogo/fyi-archive/blob/main/docs/copyright-and-licensing.md),
[ethics](https://github.com/edithatogo/fyi-archive/blob/main/docs/ethics-and-compliance.md),
and [notice](https://github.com/edithatogo/fyi-archive/blob/main/NOTICE.md) documentation.

## Citation

```bibtex
@dataset{{mordaunt_{instance.id.replace("-", "_")}_archive,
  author = {{Dylan Mordaunt}},
  title = {{{instance.title}}},
  year = {{2026}},
  url = {{https://huggingface.co/datasets/{instance.hf_repo_id}}}
}}
```
"""
