# Separate FOI site Internet Archive snapshots

The `foi_site_internet_archive.yml` workflow refreshes a cumulative Wayback CDX
snapshot every week for each configured FOI site. It does not contact an origin
site and it cannot publish data remotely.

Each site has:

- a stable, filesystem-safe archive identity;
- one or more site-specific Wayback URL patterns;
- an independent workflow artifact named with that site identity and run ID;
- a manifest recording checksums, retrieval failures, source, country, site
  kind, and the explicit `origin_contacted: false` boundary.

The inventory combines every `internet_archive`-enabled entry in
`fyi_archive.instances` with the additional and non-Alaveteli targets in
`configs/additional_foi_archive_sites.json`. Adding a site to either registry
automatically includes it in the next scheduled matrix.

Workflow artifacts are retained for 90 days. Durable publication to the
site-specific Hugging Face repositories is a separate, confirmation-gated
operation; a successful scheduled snapshot must not be described as published.
