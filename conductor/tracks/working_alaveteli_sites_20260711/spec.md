# Working Alaveteli sites

Track ID: `working_alaveteli_sites_20260711`

## Goal

Add the four independently verified non-NZ/non-AU Alaveteli deployments with
public authority catalog exports to a slow, sequential, opt-in archive workflow.

## Scope

- Register Sweden, Ukraine, Uruguay, and Georgia with independent catalog and
  capture URLs.
- Discover authority catalogs through the existing fyi-cli delegation.
- Run deterministic scheduled dry runs and explicitly gated overnight live runs.
- Bound request count, runtime, concurrency, retry behavior, and inter-request
  delay; retain per-site evidence artifacts.

## Non-goals

- No write or submission operations.
- No proxy, stealth, CAPTCHA bypass, or access-control circumvention.
- No claim that a site is fully archived until a successful non-dry-run artifact
  demonstrates capture and manifest evidence.
