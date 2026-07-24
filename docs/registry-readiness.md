# Archive Registry Readiness

Status: `repository_ready_external_gates_pending`

Roadmap: `archive_registry_readiness_20260721`

Evidence reviewed: 2026-07-24

- Parent issue: [#226](https://github.com/edithatogo/fyi-archive/issues/226)
- Zenodo snapshot: [#227](https://github.com/edithatogo/fyi-archive/issues/227)
- FAIRsharing eligibility: [#228](https://github.com/edithatogo/fyi-archive/issues/228)

## Repository contract

`fyi-archive` is an orchestration and distribution repository. It does not
create rights in archived material. Source-declared licences, attribution,
rights notices, and takedown controls remain attached to archive records.
Repository code is MIT-licensed; archived data retains source rights.

The archive publication surfaces are Hugging Face for operational derived data,
Zenodo for immutable DOI snapshots, OSF where configured, and GitHub release
assets for versioned evidence. Publication workflows are draft-first and
protected production steps remain external gates.

## FAIRsharing boundary

FAIRsharing describes and curates database/repository records and exposes
digital-object types such as datasets, documents, and software. `fyi-archive`
has a persistent public DOI, public documentation, versioned metadata, and
searchable mirror surfaces, so it is a plausible **candidate database record**.
An authenticated FAIRsharing submission and curator review are still required.
No submission, eligibility decision, FAIRsharing identifier, or curator
acceptance is claimed.

## Verified Zenodo evidence

The public Zenodo API was queried on 2026-07-24 and returned:

- record: `21338285`;
- DOI: `10.5281/zenodo.21338285`;
- title: `fyi-archive: A read-only full-site archive of fyi.org.nz (NZ Official Information Act request register)`;
- publication date: `2026-06-27`;
- files: `9`;
- last updated: `2026-07-13T22:18:44.617617+10:00`.

This evidence satisfies the repository-side assessment for issue #227. Updating
or closing the GitHub issue remains a separate external action.

## Evidence required for closeout

- A versioned archive manifest and rights/provenance evidence.
- A public Zenodo record or documented external disposition. **Verified.**
- A searchable service description and persistent identifier. **Available.**
- A FAIRsharing submission and curator disposition, if pursued. **Not submitted.**
