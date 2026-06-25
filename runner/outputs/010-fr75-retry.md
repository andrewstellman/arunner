# Output for 010-fr75-retry.md
**Status:** completed

## Summary
FR-75 per-job retry policy implemented on a dedicated worktree/branch off `main`
(post-FR-76). A job that hits a **retryable terminal** — `failed` (a worker
`FAILED`/`ABANDONED` sentinel, or a dead shell PID — the gen-007 "child runner
exited 1" transient abort) or a **FR-74 stall-reclaim** (`abandoned`) — is
**requeued** for another attempt while its persisted attempt count is below the
per-job **`max_attempts`** (default 1 = no retry, unchanged), becoming
dispatch-eligible after **`retry_backoff_seconds`** (driven by the `ARUNNER_NOW`
clock — no real sleeps). Only an exhausted budget lets the terminal stand. This
**lands the `stall_retries` seam** FR-74 reserved. Single-prompt scope;
stdlib-only (NFR-3). **3-panel self-Council: unanimous SHIP** (one round-1 FIX).

## Design

### `max_attempts` + `retry_backoff_seconds`
- Per-job optional `max_attempts` (int ≥ 1; **default 1 = no retry**) = the TOTAL
  number of dispatch attempts including the first.
- Per-job optional `retry_backoff_seconds` (number ≥ 0; default 0) = delay before
  a requeued attempt becomes dispatch-eligible (on the `ARUNNER_NOW` seam).
- Both added to **both** `plan.schema.json` copies (byte-identical) on all five
  job modes, plus `tick.py` `_COMMON_JOB_KEYS`, plus `check_plan` validation
  (`max_attempts ≥ 1`, `retry_backoff_seconds ≥ 0` — number, rejects bool/string).

### Requeue point (engine)
Three new helpers — `_retry_policy` (reads the two knobs, defaults `(1,0)`),
`_maybe_retry` (requeue-or-leave-terminal decision), `_requeue_for_retry` (the
reset) — wired at **every** retryable-terminal site in `_advance`:
1. the FAILED/ABANDONED heartbeat reap (`_move_to_results` then `_maybe_retry`
   before setting `failed`);
2. the dead-shell-PID failure (`_synthesize_failure(...,"failed")` then
   `_maybe_retry`);
3. the FR-74 stall-reclaim caller (`_maybe_retry` **before** `_reclaim_stalled`).

`auth_or_launch_failed` and `completed` are **not** wired → never retried.

`_requeue_for_retry` (resume-not-restart): drops the just-written result sentinel,
**restores the `queue/` claim token** (disk-truth parity with a fresh queued run),
**rotates/clears the watched heartbeat** (so a stale terminal line can't re-reap
the new attempt — the heartbeat-isolation mechanism), keeps the worker's OUTPUT
(target repo) untouched, **pops `done_checked`** (so FR-76 `done_check` is
re-derived on the retry), pops `started` (the retry re-acquires a fresh pool
slot), and arms `retry_not_before = now + backoff`.

`_dispatch`: increments the persisted `attempts` once per fresh single-prompt
claim; a queued run with `now < retry_not_before` is skipped (held `queued`,
holding no slot) — checked before the FR-76 done_check so a backed-off retry isn't
probed early.

### The `stall_retries` folding (decision: supersede)
`max_attempts` is the **unified** retry budget for **both** retryable terminals.
`stall_retries` (FR-74's reserved field) is **superseded** — still accepted +
validated at `--check` for plan back-compat, but **no longer read by the engine**.
Justification: `stall_retries` never had runtime effect (FR-74 always abandoned at
the default 0), so nothing regresses — a clean supersede, not a behavior change.
(Comment + the FR-74 `--check` block updated to say so.)

### End-state-for-abandoned decision (justified)
A stall-reclaimed job that **exhausts** its budget ends **`abandoned`**, NOT
`failed` — preserving FR-74's honest semantics ("the engine gave up *waiting*; it
did not *observe* a failure"). Implemented structurally: the stall path calls
`_maybe_retry` BEFORE `_reclaim_stalled`, so the exhausted case falls through to
`_reclaim_stalled` → `abandoned`. A `failed` reap that exhausts stays `failed`.
The terminal stays true to its cause.

### Transient-vs-fatal default (justified)
Only `failed` and stall-reclaimed `abandoned` are retried; `auth_or_launch_failed`
(auth/launch/pre-flight) is never retried — it won't succeed on a blind re-run, so
it never burns attempts. This is the natural transient-vs-fatal split with no
extra config (the instruction made per-job classification optional; the default
split covers the gen-007 case). Pinned by the C-F1 test.

## Before / after
- **Before:** a `FAILED`/`abandoned` job stayed terminal; gen-007's ~20%
  transient-abort rate needed manual per-job wrapper re-runs.
- **After:** with `max_attempts > 1`, a retryable terminal auto-requeues (resume,
  not restart) up to the cap; a genuinely-stuck job still ends terminal (bounded,
  never infinite). With `max_attempts:1`/absent, behavior is byte-identical to
  before FR-75.

## Files created / changed
| Path | Lines | Note |
|------|-------|------|
| `arunner/engine/tick.py` | +171/-~9 | `DEFAULT_MAX_ATTEMPTS`/`DEFAULT_RETRY_BACKOFF_SECONDS`; `_retry_policy`/`_maybe_retry`/`_requeue_for_retry`; wiring at 3 retryable sites in `_advance`; `_dispatch` backoff gate + attempt increment; `_COMMON_JOB_KEYS`; `check_plan` validation; `stall_retries` supersede comment |
| `schemas/plan.schema.json` | +14/-7 | `max_attempts` + `retry_backoff_seconds` defs + on all 5 job-mode `oneOf` branches |
| `plugins/arunner/skills/arunner/schemas/plan.schema.json` | +14/-7 | byte-identical copy |
| `references/STATE_MACHINE.md` | +40 | retryable-terminal → requeue edge + bullet + states-table note |
| `plugins/arunner/skills/arunner/references/STATE_MACHINE.md` | +40 | byte-identical copy |
| `docs/REQUIREMENTS.md` | +20 | FR-75 + US-22 + UC-18 + §9 VERIFIED row |
| `tests/test_run_robustness.py` | +228 | 9 `RetryPolicy` + 3 `CheckValidation` tests |
| `runner/reviews/010_self_council/{A,B,C,SYNTHESIS}.md` | new | 3-panel self-Council |

## Commits made (branch `fr75-retry`, local only — NOT pushed/merged)
- **`c3c80cd`** — FR-75 per-job retry policy (impl + schema + tests + docs).
- **`e3d666c`** — self-Council C-F1 (auth/launch-fail not-retried pin) + 010 council artifacts.

Worktree `~/Documents/arunner-fr75`, branch **`fr75-retry`** off `main` (`ed35f12`).

## Acceptance criteria — pass/fail per item
| Instruction item | Result |
|---|---|
| 1. `max_attempts` (both schema copies byte-identical) + `retry_backoff_seconds` + `--check` (`max_attempts ≥ 1`, backoff ≥ 0) | **PASS** — `diff` clean; `_check` validates both |
| 2. Requeue on retryable-terminal up to the cap; end-state-for-abandoned decided + justified | **PASS** — wired at 3 sites; exhausted stall-reclaim ends `abandoned` (justified) |
| 3. Resume-not-restart; compose with FR-76 (now-done retry skipped, no wasted attempt) | **PASS** — `test_retry_skipped_when_done_check_now_satisfied` (attempts==1) |
| 4. Land the `stall_retries` seam (folded into `max_attempts`; back-compat) | **PASS** — superseded + still `--check`-accepted; `test_stall_reclaimed_job_is_requeued_when_under_cap` |
| 5. FR-6 no-double-dispatch; terminal-`failed` reachable after the cap; transient-vs-fatal default; stdlib-only | **PASS** — `test_no_double_dispatch_on_requeue`; cap pin; C-F1 fatal-not-retried pin; NFR-3 intact |
| THE pin: retry-then-succeed (mutation: remove requeue ⇒ bite) | **PASS** — `test_retry_then_succeed`; mutation bit |
| Cap honored (mutation: off-by-one / no cap ⇒ bite) | **PASS** — `test_cap_honored...`; no-cap mutation bit |
| backoff via `ARUNNER_NOW` | **PASS** — `test_backoff_delays_redispatch`; ignore-backoff mutation bit |
| stall-reclaim path requeued | **PASS** — `test_stall_reclaimed_job_is_requeued_when_under_cap` |
| Full suite green ×3 (+ Python version) | **PASS** — 506 ×3, Python 3.14.6 |

## Council (required)
**3-panel self-Council: unanimous SHIP** — `runner/reviews/010_self_council/SYNTHESIS.md`.
One round-1 FIX: **C-F1** — the transient-vs-fatal default ("`auth_or_launch_failed`
never retried") was asserted but unpinned → added
`test_auth_or_launch_failed_is_not_retried`, mutation-verified (wiring
`_maybe_retry` into the launch-fail path bites). Ratified scope: retryable set =
{`failed`, stall-reclaimed `abandoned`}; exhausted end-state by cause; single-prompt
scope (multistep retry = follow-up); heartbeat rotation = the isolation mechanism.

### Mutation-verify evidence (impl committed `c3c80cd` FIRST; restored via `git checkout`)
| Pin | Mutation | Result |
|---|---|---|
| `test_retry_then_succeed` | `_maybe_retry` always returns False (no requeue) | **bit** (4 retry pins failed) |
| `test_cap_honored...` | remove the cap guard (always requeue) | **bit** (+ back-compat pin) |
| `test_backoff_delays_redispatch` | ignore `retry_not_before` | **bit** |
| `test_retry_skipped_when_done_check_now_satisfied` | don't pop `done_checked` on requeue | **bit** |
| `test_auth_or_launch_failed_is_not_retried` (C-F1) | wire `_maybe_retry` into the launch-fail path | **bit** |

## Tests
Baseline **494** → final **506** passed ×3, **1 skipped** (`python3 -m pytest tests/`),
Python **3.14.6**. +12 (9 `RetryPolicy` incl. C-F1 + 3 `CheckValidation`).
stdlib-only engine preserved (NFR-3 — no new runtime dependency; reuses
`glob`/`subprocess`/`json`/`Path`). Schema (both copies) + STATE_MACHINE (both
copies) byte-identical (`diff` clean).

## §9 rows flipped
One **VERIFIED** row added (FR-75 / US-22 / UC-18) — per-job retry policy. No
existing row changed; no number reuse (US-22 / UC-18 next-free after FR-76's
US-21 / UC-17). STATE_MACHINE (both copies): retryable-terminal → requeue edge +
the attempt-cap terminal + a states-table note.

## Notable observations
- **Disk-truth on requeue:** a requeue must restore the `queue/` claim token
  (consumed when the prior attempt was claimed) — otherwise the re-dispatch sets
  state `claimed` but writes no claim lock (caught by `test_no_double_dispatch_on_requeue`,
  which initially failed `0 != 1`). Fixed: `_requeue_for_retry` re-writes the token.
- **Heartbeat re-reap hazard:** without clearing the watched heartbeat on requeue,
  the stale FAILED line stays in the tail and `_terminal_status_of` (first terminal
  in the tail wins) re-reaps the new attempt instantly — so heartbeat rotation is
  load-bearing for retry to function at all (not just hygiene).
- **One FR-20 edge (NOTED, ratified):** the rotation truncates an external
  `heartbeat_path` file; acceptable (it is the engine's heartbeat) — full
  per-attempt heartbeat-file isolation is a follow-up.

## Next action expected from orchestrator
Independent verification of `fr75-retry` (`c3c80cd` + `e3d666c`), then land on
`main` (operator merges; the worker does not push/merge). Per
`docs/PLANNED_run_robustness.md` §8, the remaining 1.1.0 single-trunk step is
**FR-77** (supervised-bounded model; **host-capability probe first**), then
doc-sync; tag `v1.1.0` when complete. Two documented FR-75 follow-ups: multi-step
job-level retry, and full per-attempt heartbeat-file isolation.
