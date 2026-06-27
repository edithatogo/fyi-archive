# Copyright & licensing provisions

This archive preserves **already-published, public** material from
[fyi.org.nz](https://fyi.org.nz/). This document records the New Zealand copyright
provisions under which that preservation and redistribution is permitted, with
citations. It is informational, not legal advice.

## 1. What is archived, and whose copyright it is

fyi.org.nz is a third-party platform (running [Alaveteli](https://alaveteli.org/))
that publishes **Official Information Act (OIA) requests and the responses to them**.
The archived items fall into three categories:

| category | typical copyright holder | notes |
| --- | --- | --- |
| OIA **responses** from public bodies (the released documents/attachments) | often **the Crown** (a NZ government department / agency) | may attract **Crown copyright** |
| **Requests** written by private citizens | the **requester** (private author) | private literary works, posted publicly on fyi.org.nz |
| **Site metadata/UI** (page chrome, feed structure) | **fyi.org.nz** / mySociety-style operators | third-party site content |

The archive does **not** create new rights and does **not** strip attribution. It
redistributes material that the source has already made public, for research and
transparency.

## 2. Statutory basis — Copyright Act 1994

Governing law: the **Copyright Act 1994**.
([NZ Legislation, public act 1994 No 143](https://www.legislation.govt.nz/act/public/1994/0143/latest/DLM345634.html))

- **Crown copyright — s.26.** Where a work is made by the Crown (or by a person
  employed/engaged by or under the direction of the Crown) and the Crown is the first
  owner, the work attracts **Crown copyright**. ([s.26](https://www.legislation.govt.nz/act/public/1994/0143/latest/DLM345634.html))
- **Term of Crown copyright — 100 years** from the end of the calendar year in which
  the work was made. ([IPONZ — Duration of copyright](https://www.iponz.govt.nz/get-ip/copyright/duration/))
- **No copyright in certain works — s.27.** Copyright (including Crown copyright) does
  **not** subsist in: Bills, Acts of Parliament, Regulations, Parliamentary Debates
  (Hansard), and decisions/judgments of courts and tribunals. ([s.27](https://www.legislation.govt.nz/act/public/1994/0143/latest/DLM345634.html);
  [NZLII consolidated s.27](https://www.nzlii.org/nz/legis/consol_act.20250919.NEW/nz-consol_acts/ca1994133/s27.html))
- **Interpretation of "the Crown" — s.2.** Includes Her Majesty, NZ Ministers of the
  Crown, NZ government departments, and Offices of Parliament.
  ([NZLII — s.2](https://www.nzlii.org/nz/legis/consol_act/ca1994133/s2.html))

> **Relevance to this archive:** some released attachments are Crown works (s.26,
> 100-year term); others — e.g. a copy of an Act or a court decision included in a
> release — are **outside copyright** by virtue of s.27. The archive preserves all of
> them faithfully and records per-item source provenance.

## 3. Crown open licensing — the NZGOAL framework

The **New Zealand Government Open Access and Licensing (NZGOAL)** framework is the
government's guidance for agencies releasing copyright works and non-copyright
material for re-use.

- NZGOAL standardises the licensing of government-held content and recommends
  **Creative Commons Attribution 4.0 International (CC BY 4.0)** for copyright works,
  with clear **"no known rights"** statements for non-copyright material.
  ([OECD Public Research Data Toolkit — NZGOAL entry](https://www.oecd.org/en/publications/access-to-public-research-data-toolkit_a12e8998-en/new-zealand-government-open-access-and-licensing-nzgoal-framework_02e176d7-en.html);
  [data.govt.nz — NZGOAL](https://www.data.govt.nz/manage-data/policies/nzgoal);
  [NZ Digital Govt — Copyright and licensing](https://www.digital.govt.nz/standards-and-guidance/governance/copyright-and-licensing))
- NZGOAL originated in **August 2010**; **NZGOAL-SE** (Software Edition, July 2016,
  LINZ) extends it to open-source software licensing.

> **Relevance:** many OIA-released government documents are already CC BY 4.0 under
> NZGOAL, or are "no known rights" material. Where the source page declares a licence,
> the archive records it per-item in the manifest (`license` field) and preserves any
> attribution/notice text verbatim.

## 4. IPONZ — what copyright protects

Per the **Intellectual Property Office of New Zealand (IPONZ)**:

- Protected works include literary, dramatic, musical, and artistic works, sound
  recordings, films, communication works, and the typographical arrangement of
  published editions (25-year term).
- Crown copyright lasts **100 years** from the end of the year the work was made.
- There is **no copyright** in NZ Bills, Acts, Regulations, Parliamentary Debates, or
  court/tribunal decisions.
  ([IPONZ — Copyright](https://www.iponz.govt.nz/get-ip/copyright/);
  [IPONZ — Duration](https://www.iponz.govt.nz/get-ip/copyright/duration/);
  [MBIE — Copyright protection in NZ](https://www.mbie.govt.nz/business-and-employment/business/intellectual-property/copyright/copyright-protection-in-new-zealand))

## 5. How this archive applies these provisions

1. **Faithful preservation only.** Content is captured verbatim (WARC/WACZ); no
   derivative edits, no stripping of attribution or existing licence statements.
2. **Per-item provenance + licence recording.** Each manifest record carries the
   source URL, capture timestamp, and — where the source declares one — the licence
   (CC BY 4.0 / "no known rights" / other) and any attribution text.
3. **Code vs data licence separation.**
   - **Code** (this repository, `fyi-cli`, and the orchestration/adapter source) is
     **MIT** — see [`LICENSE`](../LICENSE).
   - **Archived data** (the captured fyi.org.nz material) retains the rights status of
     the source: Crown works under NZGOAL (CC BY 4.0 / "no known rights"), s.27
     material that carries no copyright, and private-author request text that remains
     the requester's. The archive asserts **no new rights** over the data.
4. **No circumvention.** Read-only access to public endpoints only; no login, no
   access controls bypassed, no non-public material sought.

## 6. Takedown

If a rights holder believes material in this archive should not be redistributed,
contact `edithatogo@users.noreply.github.com` (or use GitHub's private vulnerability
reporting). The item will be reviewed and, where appropriate, withdrawn from
subsequent mirror publications pending resolution.

## Citations

- Copyright Act 1994, NZ public act 1994 No 143 —
  https://www.legislation.govt.nz/act/public/1994/0143/latest/DLM345634.html
  (s.26 Crown copyright; s.27 no copyright in certain works; s.2 interpretation)
- IPONZ — Copyright — https://www.iponz.govt.nz/get-ip/copyright/
- IPONZ — Duration of copyright — https://www.iponz.govt.nz/get-ip/copyright/duration/
- NZGOAL (OEGL Public Research Data Toolkit entry) —
  https://www.oecd.org/en/publications/access-to-public-research-data-toolkit_a12e8998-en/new-zealand-government-open-access-and-licensing-nzgoal-framework_02e176d7-en.html
- NZGOAL (data.govt.nz) — https://www.data.govt.nz/manage-data/policies/nzgoal
- NZ Digital Government — Copyright and licensing —
  https://www.digital.govt.nz/standards-and-guidance/governance/copyright-and-licensing
- MBIE — Copyright protection in New Zealand —
  https://www.mbie.govt.nz/business-and-employment/business/intellectual-property/copyright/copyright-protection-in-new-zealand
