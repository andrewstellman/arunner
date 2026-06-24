# Panel C — tests / honesty (instr 006, FR-74 + FR-73)

Scope: both load-bearing pins present + mutation-bite; FR/US/UC added without number
reuse; §9 honest; the Step-0 gen-007 calibration finding recorded.

## Round 1 — findings

1. **Both load-bearing pins present + mutation-verified — OK.**
   - `test_pool2_two_stalled_with_queue_drains_not_halt` (the gen-007 drain).
     Mutation: `if (now - mtime) > reclaim_secs and out_stale:` → `if False and …`.
     Observed: both slots stay `stalled`, no dispatch, the tick's continuation verdict
     is `HALT:stalled` → test FAILs. Restored → PASS.
   - `test_stalled_but_output_fresh_is_NOT_reclaimed` (the quiet-but-working guard).
     Mutation: `out_stale = out_age is not None and out_age > stall_secs` →
     `out_stale = True`. Observed: the still-writing worker is reclaimed `abandoned`
     → test FAILs. Restored → PASS.
   Both bites executed in-tree on Python 3.14.6, 2026-06-24.

2. **No number reuse — OK.** FR-73 + FR-74 are next-free after FR-72; US-19 + US-20
   after US-18; UC-15 + UC-16 after UC-14. FR-61/US-17 (shipped) untouched.

3. **§9 honest — OK.** Two VERIFIED rows added, each citing the real test names in
   `test_run_robustness.py` and the mutation bites. No existing row altered.

4. **Display-only invariant pinned — OK.** `test_out_age_is_display_only_not_lifecycle`
   asserts a run with a real `COMPLETED` terminal but STALE output is reaped
   `completed` (output staleness never drives doneness), and the FR-74 *guard* biting
   is proven separately by the drain pin (it reads the data signal, not the column).

5. **Coverage breadth — OK.** Beyond the two pins: reclaim-mechanics, idempotent
   comeback, HALT-still-reachable, shell parity, below-threshold reversibility,
   multistep reclaim, the FR-73 data layer (newest-mtime / globs-scope / bounded /
   VCS-pruned / unmeasurable), display rendering, and `--check` validation (20 tests).

### Round-1 ITEM TO RATIFY (C-R1) — `stall_retries` is validated but inert in FR-74

The instruction lists `stall_retries` (suggested default 1) in the schema and a
conditional `test_stall_retry_once_then_abandon` "(if requeue is the default)". I
chose **abandon-as-default** (`stall_retries` default 0; FR-74 never requeues) and
added `stall_retries` as a validated-but-reserved knob for FR-75. Is a validated knob
that FR-74 does not act on *honest*?

**Ratified — yes, with the rationale documented in three places** (schema description,
REQUIREMENTS FR-74, the commit body):
- The engine is **signals-free / cross-platform** (`tick.py` module contract: "no
  signals") — it cannot SIGKILL a stuck shell worker; and a subagent reclaim is an
  **accounting free, not a kill**, so the un-killed worker would race a re-dispatch on
  the same heartbeat file. Safe requeue therefore needs FR-75's resume-not-restart +
  heartbeat isolation, which is out of scope here.
- FR-74's guarantee is "continue past stall" = free the slot for the **queue**;
  re-running the abandoned job's own work is a *different* concern (FR-75). The gen-007
  fix (free `defu`'s slot → drain the 43-queue) needs no requeue.
- Forward-declaring the field (validated `>= 0`) so FR-75 needs no schema change
  matches the codebase precedent (`subagent_hard_cap_minutes`). The conditional pin
  is replaced by `test_stall_retries_must_be_non_negative` (the field is accepted/
  validated) — honest about what ships.

This is a Council scope decision the instruction explicitly delegates ("Council picks
requeue-vs-abandon as the default").

### Round-1 ACTION (C-R2) — record the Step-0 calibration finding

The §9 row points at `outputs/006` for the gen-007 calibration. **Action:** the output
file MUST carry the frozen finding (defu genuinely hung / goshs alive-but-quiet, with
the timestamps). Confirmed done in `outputs/006-continue-past-stall.md`.

## Round 2 — verdict

Both pins bite; numbering clean; §9 honest; the `stall_retries` deferral is ratified
and documented; the calibration finding is recorded in the output.

**SHIP.**
