# Initial Concept (verbatim user brief)

> The user's original setup brief, captured verbatim as the authoritative input to the
> Conductor setup. Requirements traceability (`requirements.md`) and the design
> (`design.md`) derive from this. Do not edit the brief; edit those derived files.

---

I want you to create a system which archives this entire site: https://fyi.org.nz/
I want it to use this tool I created: http://github.com/edithatogo/fyi-cli
I want it to use this git repo: https://github.com/edithatogo/fyi-archive
I also want it to create a copy in my hugging face: https://huggingface.co/edithatogo (the cli tool is installed and there's tokens around)
I want this to follow the conventions of other archives in my github and hugging face: https://github.com/edithatogo/
I want it to setup an archive for zenodo and osf
In the initial phase, we won't be analysing it at all, just storing it, read only
It should start by initiating the historical storage, then by setting up the prospective archiving
There should be dynamic versioning and releases using the github actions
You should set this up like other archives of mine: https://github.com/edithatogo/hathi-nz, https://github.com/edithatogo/sm-govt-nz,
https://github.com/edithatogo/corpus-legislation-nz, https://github.com/edithatogo/corpus-nz-hansard,
https://github.com/edithatogo/corpus-cases-medilegal-nz

It should be entirely automated, using bleeding edge libraries, tools, cicd, code quality, checks, etc.

---

## Decisions confirmed with the user (during planning)

1. **Historical seed discovery:** search-feed walker (enumerate via fyi.org.nz
   advanced-search Atom feeds + their `.json` equivalents, date-windowed, paginated),
   driving per-request capture.
2. **Per-request capture scope:** request JSON + rendered HTML page + all attachment
   binaries (full faithful snapshot).
3. **Mirror targets:** all three — Hugging Face (live), Zenodo (annual DOI snapshot),
   OSF (project mirror).
4. **Repo structure:** `fyi-archive` as its own standalone repo, pushed to the existing
   empty `edithatogo/fyi-archive` remote, then added as a submodule entry in the
   `legal-nz` workspace (matching how all sibling archives are wired).

## User direction during execution

- **"Make certain you aren't implementing the tracks, just creating them"** — this
  setup phase defines tracks (spec + plan) only; it does not implement harvesters or
  publishers.
- **"You can create all of the other tracks you think are necessary too."** — the
  track set below is comprehensive.
- **"My preference is that you actually use fyi-cli, improving and adding features if
  necessary"** — capture/enumeration/diff/health capabilities are added as tracks
  *inside* `fyi-cli`; `fyi-archive` is a thin orchestration + distribution consumer.
