# Backfill ops runbook: drain → publish → verify

Operational procedure for advancing the live FYI historical corpus after
orchestration tracks are delivered. Companion to
[historical-seed-runbook.md](./historical-seed-runbook.md).

Controller state lives in GitHub issue **#9**
(`label: fyi-backfill-state`, compressed `zlib+base64` body).

---

## Pipeline shape

```text
Automated Historical Backfill  →  Historical Backfill Batch  →  Merge Backfill Artifacts
        (controller)                    (workers + artifacts)         (chunk → merged)
                                                                              │
                                                                              ▼
                                                              Publish Archives / HF Sync
                                                                              │
                                                                              ▼
                                                              Archive Health Monitor / doctor
```

| Stage | Workflow | Advances |
| --- | --- | --- |
| Dispatch | `automated_historical_backfill.yml` | `dispatch_next_id`, pending batch rows in issue #9 |
| Capture | `historical_backfill_batch.yml` | GHA artifacts `historical-backfill-<from>-<to>` |
| Merge | `merge_backfill_artifacts.yml` | pending → `merged`, `next_id` |
| Publish | `publish_archives.yml` (+ `hf_sync.yml`) | HF/OSF/Zenodo mirror contents |
| Verify | `archive_health_monitor.yml` / `fyi-archive doctor` | parity + coverage signals |

`conductor/archive_health.json` is **gitignored**. Prefer GHA artifacts and issue #9
over a local zeroed copy.

---

## Investigation snapshot (2026-07-09)

| Signal | Observation |
| --- | --- |
| Controller | Succeeds on schedule; plan is `{ complete: true, planned_count: 0, next_id: 250001 }` |
| Dispatch range | `id_to=250000` fully planned (`dispatch_next_id=250001`) |
| Cursor | `next_id ≈ 142501` (merge cursor) |
| Pending | **~195** batches still `status: pending` from ~`142501` upward |
| Workers | No new `Historical Backfill Batch` runs since **2026-07-07** |
| Merges | Last successful merge **2026-07-07**; same day many merges **cancelled** in a burst |
| Captured (state) | ~**33 244** `captured_records` across batches |
| Mirrors | Health monitor still **HF/OSF/Zenodo = 0** (run 28989825250) |
| Artifacts | Recent worker artifacts still present; expiry ~**2026-10-05** |

### Root cause (merge stall)

1. **Dispatch is done, merge is not.** The controller only plans *new* ID windows.
   When `dispatch_next_id > id_to`, it logs `No worker batches to dispatch` and does
   **not** re-drive merges for leftover `pending` rows.
2. **Cancellation storm (2026-07-07).** Many concurrent `Merge Backfill Artifacts`
   runs were cancelled within seconds of each other (pre–serialize fixes in
   PRs #31 / #32). Cancelled merges never called `mark_merged_batches`, so issue #9
   still shows `pending`.
3. **Pending rows lack `worker_run_id`.** State stores `controller_run_id` + label
   only. Manual drain must rediscover worker `run_id`s (artifact names /
   `workflow_run` history) before re-dispatching merge.
4. **Mirror gap.** Merge artifacts are not automatically published to HF. Empty
   mirror counts are expected until **Publish Archives** (or an equivalent upload)
   consumes merged manifests.

---

## Phase A — Drain pending merges

### A1. Decode current state

```bash
gh issue view 9 --json body -q .body > /tmp/backfill-body.json
# payload is zlib+base64; decode with scripts/backfill_state helpers or:
uv run python - <<'PY'
import json, zlib, base64
from pathlib import Path
obj = json.loads(Path("/tmp/backfill-body.json").read_text())
state = json.loads(zlib.decompress(base64.b64decode(obj["payload"])))
pending = [b for b in state["batches"] if b.get("status","pending") == "pending"]
print("next_id", state.get("next_id"))
print("dispatch_next_id", state.get("dispatch_next_id") or state.get("summary",{}).get("dispatch_next_id"))
print("pending", len(pending))
print("summary", state.get("summary"))
for b in pending[:20]:
    print(b)
PY
```

### A2. Map pending labels → worker run IDs

For each pending `label` (e.g. `142501-143000`):

1. Search recent successful workers for matching artifact names
   (`historical-backfill-<chunkFrom>-<chunkTo>` where chunks sit inside the label
   span; chunk size defaults to 50).
2. Or list runs created around the `controller_run_id` timestamp:

```bash
gh run list --workflow "historical_backfill_batch.yml" \
  --status completed --limit 100 \
  --json databaseId,createdAt,conclusion,url
# Then for a candidate:
gh api "repos/edithatogo/fyi-archive/actions/runs/<RUN_ID>/artifacts" \
  --jq '.artifacts[].name'
```

Confirm artifacts are **not** `expired: true` before merging.

### A3. Re-run merge (prefer bulk `run_ids`, still one *merge job* at a time)

After #31/#32, do not fan out many concurrent merge *workflow runs*. Since #33 the
merge workflow accepts either `run_id` or multi-value `run_ids` (commas, spaces, or
newlines) and downloads each worker's artifacts in one job:

```bash
# Single worker
gh workflow run merge_backfill_artifacts.yml \
  --ref main \
  -f state_label=fyi-backfill-state \
  -f dry_run=false \
  -f run_id=<WORKER_RUN_ID>

# Bulk (preferred for the ~195-pending backlog once run IDs are known)
gh workflow run merge_backfill_artifacts.yml \
  --ref main \
  -f state_label=fyi-backfill-state \
  -f dry_run=false \
  -f run_ids='28860349310,28860348191,28860346970'
```

Wait for each merge job to finish before starting another. Optional dry-run first
(`dry_run=true`) to validate downloads without mutating issue #9.

### A4. Confirm drain progress

Re-decode issue #9. Targets:

- `pending_batches` decreasing toward **0**
- `next_id` advancing toward `dispatch_next_id` / `id_to + 1`
- No new cancellation storms on the merge workflow

If artifacts expired for a pending label, **re-dispatch that ID window only** via
`historical_backfill_batch.yml` (manual `id_from`/`id_to`), then merge that new
worker run. Do not reset the whole controller range.

---

## Phase B — Publish merged corpus

When pending is drained (or you have a coherent merged manifest artifact set):

1. **Publish Archives** (workflow_dispatch on `main`), with targets appropriate
   for the environment (HF required for live; Zenodo/OSF draft-first).
2. Confirm HF repo `edithatogo/fyi-archive-nz` (repo variable `HF_REPO_ID`) shows a
   non-zero `manifests/latest_manifest.json` `record_count`.
3. Optionally run **Hugging Face Sync** to exercise restore → diff → verify once
   the dataset is non-empty.

Do not expect scheduled HF Sync alone to invent records: it syncs against whatever
is already on HF / local restore paths.

---

## Phase C — Verify health

1. Run **Archive Health Monitor** (schedule or workflow_dispatch).
2. Or locally (with secrets/env for mirrors):

```bash
uv run fyi-archive doctor
# writes conductor/archive_health.json (gitignored)
```

3. Success criteria for this phase:

| Check | Goal |
| --- | --- |
| HF record count | `> 0` and ≈ merged/captured magnitude |
| Mirror parity | Within doctor tolerance of local/manifest |
| Coverage | Moving toward 60% target (full-site is longer-term) |
| Issue #9 | `pending_batches == 0`, `complete` consistent with range |

4. Update `conductor/operations_status.json` after a meaningful ops change so the
   next `/conductor-status` read is not stale.

---

## When the controller looks “green” but nothing moves

| Log / state | Meaning | Action |
| --- | --- | --- |
| `No worker batches to dispatch` + `complete: true` | ID range fully planned | Drain merges / publish; do not expect new workers |
| `Active Historical Backfill Batch runs: N` with N ≥ cap | Slots full | Wait or inspect stuck workers |
| Many merge runs `cancelled` in same second | Concurrency collision | Serialize merges; never bulk-dispatch merges |
| Health HF count 0 after controller success | Publish gap | Phase B |
| Pending labels without artifacts | Retention loss | Re-run batch for that ID window only |

---

## Safety

- Use a separate `state_label` (e.g. `fyi-backfill-state-smoke`) for experiments.
- Prefer **serial** merge and modest `max_batches` overnight caps already in the
  controller.
- Production Zenodo still requires protected environment + confirmation string.
- Do not force-push controller state by hand unless you understand
  `scripts/backfill_state.py` merge semantics.
