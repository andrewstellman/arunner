# Panel A — state-machine / correctness (instr 006, FR-74 + FR-73)

Scope: the `stalled → abandoned` reclaim transition, slot accounting, the
output-fresh guard (no false-abandon of a live worker), `stalled ↔ running`
reversibility below the reclaim threshold, and the reclaimed-comeback race.

## Round 1 — findings

1. **Transition correctness — OK.** Reclaim reuses `_synthesize_failure(run_dir, r,
   "abandoned", …)` — the *same* idempotent terminal-synthesis path CANCEL (FR-39)
   uses. `abandoned` is in `_TERMINAL_STATES` and NOT in `_INFLIGHT_STATES`, so the
   reclaimed run leaves the in-flight set and its slot frees. `_dispatch` (same tick,
   after `_advance`) then fills the slot from the queue. Verified by
   `test_pool2_two_stalled_with_queue_drains_not_halt` and
   `test_reclaimed_stall_is_abandoned_and_frees_slot`.

2. **No false-abandon of a live worker — OK (load-bearing).** The reclaim fires only
   when `(now - hb_mtime) > stall_reclaim_secs` **AND** `out_age is not None and
   out_age > stall_secs`. A still-writing worker (OUT-AGE fresh) is held, never
   abandoned — `test_stalled_but_output_fresh_is_NOT_reclaimed`, mutation-verified
   (drop the guard ⇒ the live worker is abandoned ⇒ bite).

3. **Reversibility below the threshold — OK.** The reclaim is nested under the same
   `elif (now - mtime) > stall_secs` branch; below `stall_reclaim_secs` the run just
   marks `stalled`, and a fresh heartbeat returns it to `running`
   (`test_below_reclaim_window_stays_stalled_and_recovers`).

4. **Comeback race — OK.** Once `abandoned` (terminal), `_advance` skips the run
   (`if state in _TERMINAL_STATES: continue`), `_dispatch` only ever dispatches
   `queued`, and the display `_reconcile_state` overlays a heartbeat-terminal only
   onto an *inflight* persisted state (`abandoned` is not inflight). So a late
   `COMPLETED`/`FAILED` from the un-killed worker cannot resurrect, double-count, or
   double-dispatch. `test_reclaimed_worker_late_terminal_does_not_resurrect_or_double_dispatch`.

5. **`mtime is None` (stat race) — OK.** Handled by the pre-existing
   `if mtime is None: pass` guard *before* the stall/reclaim `elif`, so an unknowable
   heartbeat mtime never triggers a reclaim (conservative).

6. **Multistep parity — OK.** `_advance_multistep` got the same guard, writing the
   entry-level result (`_write_entry_result`) + step synth before taking the run
   `abandoned`, so the roll-up stays consistent (`test_multistep_stall_reclaimed`).

### Round-1 ACCEPTED TRADEOFF (ratified, not a blocker)

- **Output-freshness window = `stall_threshold_minutes` (45m default).** A worker
  that legitimately *reads* (writes nothing) for >45m AND whose heartbeat keepalive
  has also died past `stall_reclaim_minutes` (90m) would be reclaimed. Calibrated
  against the gen-007 evidence (`source-controller` read ~34m < 45m while alive →
  protected; `defu` was output-silent ~1h53m → correctly reclaimable). A worker
  silent on BOTH heartbeat (90m) and output (45m) is reasonably judged hung; the
  cost is bounded (its own job, not the batch) and the FR-72 720-min hard cap is the
  slower backstop. **Ratified as the right default**; an operator can widen
  `stall_reclaim_minutes` to be more conservative.

## Round 2 — verdict

All round-1 items are OK; the one tradeoff is ratified and documented. The
`out_stale = is-not-None AND > stall_secs` form means an **unmeasurable** output area
(None) conservatively HOLDS — the engine never reclaims on the mere absence of a
signal (`test_unmeasurable_output_area_is_none` + the guard expression).

**SHIP.**
