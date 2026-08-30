# Raw-retention incident and repair — 2026-08-30

Guarded recovery run 33305733977 released failed owner 31929819944 without changing prior coverage. Bounded one-request run 33305989413 then succeeded and advanced credited coverage from 17225 to 17226. Its artifact 9730497676 (SHA-256 67bb806bd47854b9ae6af4357f9ec6206baa0c52a1f9633bdc493579db9b17f2) contained only the ledger, manifest and process sidecars: the upload list omitted data/raw/requests, data/attachments, data/warc and dist/site_snapshots. The new raw validator rejects that downloaded artifact. Credited progress is therefore not raw-preservation coverage; historical gaps remain open and are not silently rewritten.

The NZ monitor (workflow 322525555) was disabled while fixing retention. No active monitor run needed cancellation. Do not enable it until a bounded hosted raw restore passes and durable publication/retention policy is reconciled. Existing credits remain unchanged; old missing raw bytes are not recovered by a new checksum.

The repair inventories every file under data and the generated WACZ directory, verifies original HTML/attachments against recorded hashes and WARC response payloads, rejects absent or corrupt objects and unsafe paths/symlinks, and bounds file count plus stored/decompressed bytes. A successful batch uploads these bytes, downloads the exact artifact ID into a clean directory, rebuilds the inventory, and only then credits the queue. The manifest hash is included in the batch evidence. This is temporary 90-day artifact retention, not public HF delivery or a durable archive.

Checked the pinned download-artifact source: artifact-ID downloads require merge-multiple=true to restore directly into the requested root. Source-tool version labels now come from installed package metadata instead of the stale hard-coded 1.2.0 string; the dependency remains locked to fyi-cli 1.2.1.

HF sync diagnosis run 33306106031 passed with one parseable dedicated summary, a rendered card and retained execution receipt. verified=null and record_count=0 describe its dry run; no public upload occurred. The previous concatenated-JSON failure was not reproduced in this hosted path. Live public readback remains pending.

Local full test harness passed 917 tests, one skip, 93.39% coverage. Stable/preview Ruff, formatting, ty and changed-workflow actionlint passed. Hosted checks and a new original-byte restore are still required. These are additional findings inside the approved recovery/raw-preservation scope, not completed global rollout.

## Stored-byte verification correction

A compressed-attachment regression reproduced a false mismatch when the verifier applied HTTP content decoding to bytes that fyi-cli had already decoded before WARC creation. The verifier now hashes the stored WARC payload stream directly, leaving compression/container bytes intact. The new regression failed before the correction and passes afterward. Full donor tests: 918 passed, one skip, 93.39% coverage; stable Ruff, preview formatting and ty passed. This does not alter preserved WARC bytes or clear source/publication gates.

## Whole-container compatibility and failure-path correction

Hosted run 33307488567 at merge 676461907887ace3f3a42a270b0b05ad0ed29ec6 failed before queue credit with ArchiveLoadFailed: non-chunked gzip file detected. No artifact was retained because failure handling preceded verification. The pinned fyi-cli archive_capture.py explicitly uses gzip.open(..., "wb") around WARCWriter(..., gzip=False). A regression recreated that exact container layout and failed before this correction.

The verifier now expands the outer gzip into a bounded temporary stream before parsing records. A shared expanded-byte budget includes all headers and non-response records, and originals remain unchanged. Tests reject excessive expansion and retain the separate compressed HTTP attachment regression. Failure retention and exact-owner release now run after capture, verification and completion, covering post-capture failures. The failed range remains uncredited; recovery must inspect that exact owner before retry. NZ monitoring stays paused; no public HF upload or completed-country claim is made.

Validation passed: 921 tests, one skip, 93.40% coverage; 14 retention tests; stable Ruff, preview formatting, repository-scoped ty and actionlint. An overly broad ty invocation initially included optional Atheris fuzz dependencies absent locally; the repository-required src scope passes. Recovery 33307589477 released only failed run 33307488567; queue remains at 17226 with no lease. New hosted raw restore remains pending.
