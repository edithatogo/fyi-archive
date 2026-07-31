# Transport-independent Wayback replay state

`fyi-archive` owns replay policy, durable state, provenance and verification.
It does not perform network access. `fyi-cli` remains the network owner and
passes immutable transport observations into the replay-state boundary.

The replay-state contract provides:

- SHA-256 content-addressed objects with symlink, traversal, collision and
  integrity checks;
- an append-only, hash-chained and fsynced attempt journal;
- atomically replaced checkpoints bound to the exact ordered selection,
  policy, producer, parser and jitter seed;
- stable retryable, terminal and complete outcome classes;
- deterministic adaptive pacing, `Retry-After` handling and circuit state
  through injected time and random sources;
- exact-canonical-URL replacement metadata candidates that remain
  `pending_replay_approval`; and
- a standalone verifier that imports no replay producer code.

The package contains no HTTP client, origin discovery or archive replay
command. A replacement candidate is metadata only and never changes active
membership. The AU regression oracle contains only approved hashes and counts;
it contains no retained or restricted source content and is not authorization.
