---
pretty_name: "fyi-archive-nz"
license: mit
language:
  - en
tags:
  - new-zealand
  - oia
  - official-information-act
  - alaveteli
  - web-archive
  - warc
  - wacz
  - legal
  - government-transparency
configs:
  - config_name: default
    data_files:
      - split: requests
        path: requests/*.parquet
      - split: authorities
        path: authorities/*.parquet
---

# fyi-archive-nz

Planned dataset card for a faithful, read-only full-site archive of
**[fyi.org.nz](https://fyi.org.nz/)** — the New Zealand Official Information Act
(OIA) request register, running on [Alaveteli](https://alaveteli.org/).

This dataset has not been published yet. The repository currently contains the
orchestration scaffold and schemas; the historical backfill and mirror publication
workflows are still pending.

## Source provenance

- **Upstream:** `https://fyi.org.nz/` (public read-only endpoints only; no auth).
- **Capture tool:** [`fyi-cli`](https://github.com/edithatogo/fyi-cli) (bulk
  enumeration + faithful WARC/WACZ capture of request metadata, rendered pages, and
  attachments).
- **Orchestration:** [`edithatogo/fyi-archive`](https://github.com/edithatogo/fyi-archive).

## Data fields (per-request record)

| field | type | description |
| --- | --- | --- |
| `request_id` | int | fyi.org.nz numeric request id |
| `url_title` | string | canonical slug (final path segment of the request URL) |
| `title` | string | request title |
| `authority` | string | public body the request was addressed to |
| `state` | string | described state (e.g. `successful`, `refused`, `waiting`) |
| `first_sent` | datetime | when the request was lodged |
| `last_updated` | datetime | upstream last-modified |
| `content_sha256` | string | SHA-256 of the captured JSON payload (content address) |
| `html_captured` | bool | whether a rendered HTML snapshot exists |
| `attachments` | list<struct> | name, url, content_type, size, sha256 |
| `warc_record_ids` | list<string> | WARC record ids for this request |

## Loading

```python
from datasets import load_dataset
ds = load_dataset("edithatogo/fyi-archive-nz", split="requests")
```

```sql
-- DuckDB over the Hugging Face mirror
SELECT authority, state, count(*) AS n
FROM 'hf://datasets/edithatogo/fyi-archive-nz/requests/*.parquet'
GROUP BY 1, 2 ORDER BY n DESC;
```

## Intended use once published

Research, legal-tech NLP, journalism, and government-transparency workloads.

## Limitations

- A point-in-time snapshot of a live site; the authoritative record is the live
  `fyi.org.nz` site. See [`NOTICE.md`](https://github.com/edithatogo/fyi-archive/blob/main/NOTICE.md).
- Not affiliated with or endorsed by the operators of fyi.org.nz.

## Copyright & licensing

Archived content is already-published public material; the dataset asserts **no new
rights** over it. Per-item `license` + `attribution` are recorded in the manifest where
the source declares them. Government-released material is typically **CC BY 4.0** under
the [NZGOAL](https://www.data.govt.nz/manage-data/policies/nzgoal) framework or
"no known rights"; Acts/Regulations/court decisions are outside copyright
([Copyright Act 1994 s.27](https://www.legislation.govt.nz/act/public/1994/0143/latest/DLM345634.html));
Crown works otherwise attract Crown copyright (s.26, 100-year term per
[IPONZ](https://www.iponz.govt.nz/get-ip/copyright/duration/)). Private-author request
text remains the requester's. The repository **code** is MIT. Full provisions and
citations: [`docs/copyright-and-licensing.md`](https://github.com/edithatogo/fyi-archive/blob/main/docs/copyright-and-licensing.md).

## Citation

```bibtex
@dataset{mordaunt_fyi_archive,
  author    = {Dylan Mordaunt},
  title     = {{fyi-archive: a read-only full-site archive of fyi.org.nz}},
  year      = {2026},
  url       = {https://github.com/edithatogo/fyi-archive}
}
```
