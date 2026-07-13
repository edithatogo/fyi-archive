# Targeted mirror verification

## Goal

Make retries of one publication mirror independently actionable when the
aggregate report contains a stale result for another mirror.

## Requirements

- A targeted verification command must fail only when the mirror(s) checked by
  that invocation fail.
- The aggregate JSON report must retain evidence for previously checked mirrors.
- Versioned verification evidence must identify the mirror(s) checked by the
  invocation and must not inherit stale failures from unrelated mirrors.
- Add regression coverage for a successful OSF retry after a stale HF failure.

## Non-goals

- Do not weaken artifact checksum, presence, or size validation.
- Do not erase aggregate historical evidence.
