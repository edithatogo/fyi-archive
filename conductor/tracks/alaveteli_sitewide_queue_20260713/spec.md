# Specification: alaveteli_sitewide_queue_20260713

## Goal

Advance the four working Alaveteli site archives beyond one-request smoke
captures using the public paginated feed, durable checkpoints, and verified
capture state.

## Requirements

- Use fyi-cli's paginated public search feed before numeric probing.
- Persist the feed checkpoint and request queue in retained site artifacts.
- Remove a queue item only after a completed ledger entry exists.
- Retry failed requests on later runs without duplicating completed captures.
- Keep one in-flight request per site and the existing host pacing.
- Fail closed for upstream HTTP 403 responses.

## Boundary

This track implements the resumable site-wide mechanism. It does not claim
that the four live sites are already completely captured; site completion is
proven only by an eventual queue-empty report and reconciled manifest.
