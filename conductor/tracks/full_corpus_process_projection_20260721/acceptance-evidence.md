# Downstream acceptance evidence

The implementation track is closed against the authoritative hosted evidence:

- `foi-process` issue `#9` records hosted live-manifest adapter acceptance in
  run `29827022746`: 33,217 current fyi-archive records converted with count
  parity and deterministic repeated SHA-256 output.
- `foi-process` issue `#9` records replay-equivalence acceptance in run
  `29827798682`: full replay and ordered incremental continuation produced
  identical canonical final snapshot hashes for 33,217 records.
- Downstream `foi-process #37` and this track's `fyi-archive #196` are closed.
- The remaining remote verification/publication item is intentionally separate
  from implementation and remains governed by `foi-process #9` and epic #36.

Local evidence complements the hosted runs: `live-acceptance.md`, the pinned
manifest/attachment digests, the deterministic shard/tombstone tests, and the
full local test suites.

## Bounded live continuation attempt (2026-07-22)

Hosted run `29890645510` attempted a bounded production continuation for IDs
1-100 with `max_requests=10`, serial capture, and a two-second interval. The
worker completed with failure and produced diagnostic artifact
`historical-backfill-1-100` (artifact `8518229875`). The source returned HTTP
403 for request 32 and subsequent reads timed out; the worker recorded 9
failed captures and refused derived export. This artifact is diagnostic only:
it is not a verified manifest/event-log deposit and must not advance the full
corpus acceptance gate.

The preserved local WARC/WACZ samples remain valid representative fixtures for
adapter and attachment verification. Full-corpus acceptance still requires a
reliable authoritative source, a zero-failure capture set (or an explicitly
reconciled archive snapshot), and manifest/event/attachment digest parity.
