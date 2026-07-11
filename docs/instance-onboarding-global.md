# Global Alaveteli instance onboarding

Extension of the English onboarding checklist for non-English instances and
jurisdictions with additional privacy, language, or residency requirements.

## Locale and source review

- [ ] Record the primary locale, supported languages, date/time conventions, and
      translated request/body fields needed for faithful capture.
- [ ] Confirm the source's public-access and robots policies in the relevant language.
- [ ] Identify the source operator, data-protection contact, and takedown process.
- [ ] Obtain a jurisdiction-specific review before handling material that may contain
      personal data, sensitive categories, or cross-border transfer restrictions.

## Privacy and minimisation

- [ ] Document the purpose, lawful basis/authority, retention period, access controls,
      and deletion/takedown process with qualified local advice.
- [ ] Do not infer that public availability removes privacy obligations.
- [ ] Do not add enrichment, profiling, OCR, translation, or entity normalisation to
      the storage-only pipeline without a separately reviewed track.
- [ ] Keep credentials, operator contacts, and private correspondence out of the
      archive; redact secrets from logs and provenance diagnostics.
- [ ] Record data residency and mirror locations before enabling publication.

## Configuration template

```toml
[instance]
id = "example-global"
base_url = "https://example.invalid"
country = "XX"
locale = "xx-XX"
hf_repo_id = "owner/example-global-archive"
rate_limit_name = "archive-discovery-example-global"
status = "experimental"
```

The instance ID, storage paths, limiter name, manifest source, and publication
repository must be unique. Catalog overrides are explicit, reviewed configuration
and must be recorded in provenance.

## Pilot gates

- [ ] Dry-run controller and schema tests pass.
- [ ] A capped, slow live smoke is approved and completed without policy or load
      concerns.
- [ ] Locale/privacy review and takedown contact are recorded.
- [ ] Manifest, checksum, provenance, and mirror verification evidence is retained.
- [ ] Promotion out of `experimental` is approved separately.

This template is operational guidance, not legal advice. Consult qualified local
advisers for GDPR, privacy, copyright, data-transfer, and retention questions.
