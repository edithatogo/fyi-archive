# Design (Mermaid)

Derived from [`requirements.md`](./requirements.md). Diagrams are the authoritative
design reference; prose clarifies intent only. (`docs/README.md` holds the
user-facing architecture summary; this file holds the full design.)

## 1. System architecture — two-repo responsibility split

`fyi-cli` owns **all** network access and capture; `fyi-archive` owns orchestration +
distribution only. Nothing in `fyi-archive` fetches from the network.

```mermaid
flowchart TB
  classDef capture fill:#e3f2fd,stroke:#1565c0
  classDef orch fill:#f3e5f5,stroke:#6a1b9a
  classDef mirror fill:#e8f5e9,stroke:#2e7d32
  classDef ext fill:#fff3e0,stroke:#ef6c00

  SITE["fyi.org.nz<br/>(Alaveteli — read-only public API)"]:::ext

  subgraph CLI["fyi-cli — capture tool  (github.com/edithatogo/fyi-cli)"]
    direction TB
    ENUM["bulk-site-enumeration<br/>search-feed walker + ID backfill"]:::capture
    CAP["faithful-archive-capture<br/>json + html + attachments → WARC 1.1 → WACZ"]:::capture
    DIFF["archival-content-diff<br/>added/updated/removed by SHA-256"]:::capture
    HEALTH["archive-health-doctor<br/>freshness · coverage · counts"]:::capture
    DB[("SQLite snapshot store<br/>(existing) + WARC/WACZ")]
    ENUM --> CAP --> DIFF --> HEALTH
    CAP --> DB
  end

  subgraph ARCH["fyi-archive — orchestration + distribution  (this repo)"]
    direction TB
    SEED["historical_seed workflow<br/>date-window fan-out · resumable ledger"]:::orch
    SYNC["hf_sync workflow<br/>restore → diff → capture-new → manifest → upload → verify"]:::orch
    PUB["publish_archives workflow<br/>build dist + provenance + SBOM"]:::orch
    ADAPT["mirror adapters<br/>HF · Zenodo · OSF"]:::orch
    META["metadata + DuckDB export<br/>Croissant · Frictionless"]:::orch
    SEED --> PUB
    SYNC --> PUB
    PUB --> ADAPT
    PUB --> META
  end

  SITE --> CLI
  CLI -->|WARC/WACZ · manifest.json/parquet · changes.json| ARCH

  ADAPT --> HF["Hugging Face<br/>(live, content-revised)"]:::mirror
  ADAPT --> ZN["Zenodo<br/>(annual DOI snapshot)"]:::mirror
  ADAPT --> OSF["OSF<br/>(project + components)"]:::mirror
  PUB --> GH["GitHub Releases<br/>+ SBOM + provenance"]:::mirror
```

## 2. Data model — WARC/WACZ as source of truth

WARC is the archival source of truth; the SQLite snapshot store, the per-request
derived view, and the manifest are all projections over it.

```mermaid
flowchart LR
  subgraph truth["Source of truth (fyi-cli)"]
    WARC[("WARC 1.1 records<br/>json · html · attachments<br/>payload sha256 digests")]
    WACZ[("WACZ packages<br/>datapackage.json + index<br/>appendable/segmented")]
    WARC --> WACZ
  end
  subgraph derived["Derived projections"]
    SQL[("SQLite request_snapshots<br/>(existing schema)")]
    FS["data/raw/requests/&lt;authority&gt;/&lt;id&gt;/<br/>request.json · page.html · attachments/"]
    MAN["manifests/latest_manifest.{json,parquet}<br/>+ authorities.json"]
    CHG["manifests/latest_changes.json"]
    DUCK["dist/fyi_archive.duckdb<br/>(read-only analytics)"]
  end
  WARC --> SQL
  WARC --> FS
  WARC --> MAN
  WARC --> CHG
  MAN --> DUCK
```

## 3. Historical seed — resumable, date-windowed, capped

```mermaid
stateDiagram-v2
  [*] --> Discover: workflow_dispatch (date window, caps)
  Discover: Walk search feeds → list url_titles
  Discover --> CheckCaps
  CheckCaps: within --max-requests/bytes/runtime/disk?
  CheckCaps --> [*]: cap hit → flush ledger + abort
  CheckCaps --> Capture: ok
  Capture: fyi-cli capture each (WARC/WACZ)
  Capture --> Ledger: append done IDs to ledger.jsonl
  Ledger --> CheckCaps
  CheckCaps --> Manifest: window exhausted
  Manifest: assemble latest_manifest.{json,parquet}
  Manifest --> PublishHF: upload_large_folder + hf-xet
  PublishHF: re-download remote manifest
  PublishHF --> Verify: SHA-256 compare
  Verify --> [*]: mismatch → fail
  Verify --> [*]: match → success
note right of Ledger
  Resumable: re-run skips IDs
  already in ledger.jsonl.
  Date-window matrix fans out
  across GHA jobs.
end note
```

## 4. Prospective sync — daily, content-addressed

```mermaid
stateDiagram-v2
  [*] --> Restore: daily cron (17 14 * * *)
  Restore: HF snapshot_download
  Restore --> Diff
  Diff: fyi-cli diff --since last
  Diff --> Classify
  Classify: added / updated / removed (by SHA-256)
  Classify --> NoChange: empty sets
  NoChange --> [*]: advance high-water mark
  Classify --> CaptureNew: added/updated exist
  CaptureNew: fyi-cli capture (new/changed only)
  CaptureNew --> Rebuild
  Rebuild: regenerate manifest + changes
  Rebuild --> Upload: upload_large_folder
  Upload --> Verify: re-download remote manifest
  Verify --> [*]: mismatch → fail (no advance)
  Verify --> [*]: match → advance high-water mark
```

## 5. Publishing — multi-mirror, draft-first

```mermaid
flowchart TB
  BUILD["publish_archives.yml<br/>build dist/"] --> BUNDLE{"publish target"}
  BUNDLE -->|huggingface| HF["HF: upload_large_folder + hf-xet"]
  BUNDLE -->|zenodo| ZD["Zenodo: create draft deposition"]
  BUNDLE -->|osf| OSF["OSF: project + components + upload"]
  BUNDLE -->|all / all_with_osf| ALL["run all enabled"]
  ZD --> ZGATE{"publish gate +<br/>zenodo-production env<br/>+ confirm string?"}
  ZGATE -->|no| ZDRAFT["leave as draft"]
  ZGATE -->|yes| ZPUB["publish DOI"]
  BUILD --> ATTEST["actions/attest-build-provenance<br/>on WACZ · DuckDB · manifest · SBOM"]
  BUILD --> REL["attach to GitHub Release<br/>(release-please)"]
```

## 6. Versioning & release flow — dynamic, via GHA

SemVer in `pyproject.toml` + `VERSION`, kept in sync by
`check_version_consistency.py`. `release-please` consumes Conventional Commits to
produce bumps, `CHANGELOG.md`, and GitHub Releases automatically.

```mermaid
flowchart LR
  CM["Conventional Commits on main<br/>feat: / fix: / chore:"] --> RP["release-please.yml"]
  RP -->|opens| PR["Release PR<br/>(bump + CHANGELOG)"]
  PR -->|merged| REL["GitHub Release v0.x.y"]
  REL --> ATT["attach dist/ artifacts<br/>+ SBOM + provenance"]
  REL --> ZD["triggers annual Zenodo snapshot (manual)"]
  VC["check_version_consistency.py"] -.->|CI gate| PR
```

## 7. CI/CD & quality pipeline

```mermaid
flowchart LR
  P["push / PR"] --> T["tests.yml<br/>uv --frozen · matrix 3.12/3.14<br/>pytest+cov · version-consistency"]
  P --> Q["code_quality.yml<br/>ruff · ty · typos · taplo · actionlint · zizmor"]
  P --> CW["codeql.yml · scorecard.yml"]
  SCH["schedule"] --> HS["hf_sync.yml (daily)"]
  SCH --> HM["archive_health_monitor.yml"]
  SCH --> PP["publish_archives.yml (weekly)"]
  FAIL["CI failures"] --> LC["ci-learning-candidates.yml<br/>→ improvement-backlog.md"]
```

## 8. State & ledger locations

```mermaid
flowchart LR
  subgraph gitignored["gitignored (data lives on mirrors)"]
    D1["data/warc/*.warc.gz"]
    D2["data/raw/requests/..."]
    D3["data/attachments/<sha256>"]
    D4["data/_state/ledger.jsonl<br/>data/_state/sync_state.json"]
    D5["dist/*.wacz · *.duckdb · provenance.json · sbom.cdx.json"]
  end
  subgraph committed["committed"]
    C1["manifests/*.schema.json (schemas)"]
    C2["metadata/ (Croissant/Frictionless, generated)"]
    C3["conductor/archive_health.json (committed by monitor)"]
  end
  D4 --> C3
```

## Design principles

1. **fyi-cli owns the network.** No fetch logic in `fyi-archive` (R-05, R-06, R-41).
2. **WARC/WACZ is the source of truth.** Everything else is a projection (section 2).
3. **Read-only & polite.** Rate-limited, robots-aware, capped (R-02, R-20, R-21, R-42).
4. **Historical before prospective** (R-13 → R-14).
5. **Draft-first, gated publication** (R-22).
6. **Automated, evidence-backed releases** (R-15, R-16, R-24).
7. **Storage-only in phase 1** — no analysis (R-03, R-04, R-28, R-29, R-51).
8. **Instance-aware orchestration** — default `nz-fyi`; multi-instance via config (R-40).
9. **Public-policy research purpose** — not AI training (R-43).

## 9. Multi-instance architecture

```mermaid
flowchart TB
  classDef capture fill:#e3f2fd,stroke:#1565c0
  classDef orch fill:#f3e5f5,stroke:#6a1b9a
  classDef mirror fill:#e8f5e9,stroke:#2e7d32
  classDef ext fill:#fff3e0,stroke:#ef6c00

  subgraph sources["Alaveteli sources"]
    NZ["nz-fyi<br/>fyi.org.nz"]:::ext
    AU["au-rtk<br/>righttoknow.org.au"]:::ext
    EN["English fleet<br/>uk-wdtk, ie, …"]:::ext
    I18N["Non-English fleet<br/>de-fds, fr-cada, …"]:::ext
  end

  subgraph cli["fyi-cli — capture only"]
    CAT["instances.toml catalog"]:::capture
    DISC["discover / bodies / tags<br/>robots + shared rate limit"]:::capture
    CAP["capture → WARC/WACZ"]:::capture
    DIFF["diff / archive-health"]:::capture
  end

  subgraph arch["fyi-archive — orchestration + distribution"]
    INST["instance + jurisdiction config"]:::orch
    SEED["seed / backfill controller"]:::orch
    SYNC["prospective sync"]:::orch
    MAN["manifest meta + partitions"]:::orch
    PUB["multi-mirror publish"]:::orch
  end

  NZ --> DISC
  AU --> DISC
  EN --> DISC
  I18N --> DISC
  CAT --> DISC
  DISC --> CAP --> DIFF
  CAP --> SEED
  DIFF --> SYNC
  INST --> SEED
  INST --> SYNC
  SEED --> MAN --> PUB
  SYNC --> MAN
  PUB --> HF["HF datasets<br/>per instance"]:::mirror
  PUB --> ZN["Zenodo / OSF"]:::mirror
```

## 10. AU jurisdiction rollout state machine

Right to Know Australia is **one** national Alaveteli instance. Jurisdictions are
body-tag partitions (`NSW_state`, `VIC_state`, …), not separate sites.

```mermaid
stateDiagram-v2
  [*] --> NSW: first production slice
  NSW --> VIC: NSW exit criteria met
  VIC --> QLD
  QLD --> SA
  SA --> WA
  WA --> TAS
  TAS --> ACT
  ACT --> NT
  NT --> CTH: federal bodies
  CTH --> OTHER: uncategorised / local residual
  OTHER --> NationalSync: merge manifests
  NationalSync --> ProspectiveAU: daily au-rtk sync
  ProspectiveAU --> [*]
```

## 11. Global Alaveteli ladder

```mermaid
flowchart LR
  NZ["NZ nz-fyi<br/>production"] --> AU["AU au-rtk<br/>state-by-state"]
  AU --> EN["English fleet<br/>uk-wdtk → ie → …"]
  EN --> I18N["Non-English fleet<br/>de / fr / es / …"]
```

## 12. Multi-instance data layout

```mermaid
flowchart TB
  DATA["data/"]
  DATA --> NZD["nz-fyi/<br/>warc · raw · _state"]
  DATA --> AUD["au-rtk/"]
  AUD --> NSW["nsw/<br/>ledger · derived"]
  AUD --> VIC["vic/ …"]
  AUD --> NAT["_national/<br/>merged manifest state"]
  DIST["dist/<instance_id>/"]
  MAN["manifests/<br/>latest may be NZ default;<br/>AU under instance paths or meta.instance_id"]
```

## 13. Conductor track → GitHub project flow

```mermaid
flowchart LR
  REQ["requirements.md<br/>R-40…R-51"] --> TR["tracks/*/spec+plan"]
  TR --> ISS["GitHub parent issue<br/>per track"]
  ISS --> SUB["Sub-issues<br/>work breakdown"]
  SUB --> PRJ["Repo project board<br/>native workflows"]
  PRJ --> RIOPA["RIOPA umbrella<br/>item mirror sync"]
```
