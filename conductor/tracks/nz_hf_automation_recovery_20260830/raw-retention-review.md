# Raw-retention incident and repair — 2026-08-30

Guarded recovery run 33305733977 released failed owner 31929819944 without changing prior coverage. Bounded one-request run 33305989413 then succeeded and advanced credited coverage from 17225 to 17226. Its artifact 9730497676 (SHA-256 67bb806bd47854b9ae6af4357f9ec6206baa0c52a1f9633bdc493579db9b17f2) contained only the ledger, manifest and process sidecars: the upload list omitted data/raw/requests, data/attachments, data/warc and dist/site_snapshots. The new raw validator rejects that downloaded artifact. Credited progress is therefore not raw-preservation coverage; historical gaps remain open and are not silently rewritten.

The NZ monitor (workflow 322525555) was disabled while fixing retention. No active monitor run needed cancellation. Do not enable it until a bounded hosted raw restore passes and durable publication/retention policy is reconciled. Existing credits remain unchanged; old missing raw bytes are not recovered by a new checksum.

The repair inventories every file under data and the generated WACZ directory, verifies original HTML/attachments against recorded hashes and WARC response payloads, rejects absent or corrupt objects and unsafe paths/symlinks, and bounds file count plus stored/decompressed bytes. A successful batch uploads these bytes, downloads the exact artifact ID into a clean directory, rebuilds the inventory, and only then credits the queue. The manifest hash is included in the batch evidence. This is temporary 90-day artifact retention, not public HF delivery or a durable archive.

Checked the pinned download-artifact source: artifact-ID downloads require merge-multiple=true to restore directly into the requested root. Source-tool version labels now come from installed package metadata instead of the stale hard-coded 1.2.0 string; the dependency remains locked to fyi-cli 1.2.1.

HF sync diagnosis run 33306106031 passed with one parseable dedicated summary, a rendered card and retained execution receipt. verified=null and record_count=0 describe its dry run; no public upload occurred. The previous concatenated-JSON failure was not reproduced in this hosted path. Live public readback remains pending.

Local full test harness passed 917 tests, one skip, 93.39% coverage. Stable/preview Ruff, formatting, ty and changed-workflow actionlint passed. Hosted checks and a new original-byte restore are still required. These are additional findings inside the approved recovery/raw-preservation scope, not completed global rollout.
