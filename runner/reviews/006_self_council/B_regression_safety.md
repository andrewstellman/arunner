# Panel B — regression-safety (instr 006, FR-74 + FR-73)

Scope: `HALT:stalled` still reachable for the genuine wedge; shell parity; CANCEL;
no double-dispatch; FR-72 launch path unchanged; OUT-AGE display-only; renderer
parity engine/monitor/tui; stdlib-only + bounded scan.

## Round 1 — findings

1. **`HALT:stalled` preserved — OK.** `_halt_reason`'s stalled branch is untouched;
   it now fires only when no slot can be freed — i.e. reclaim is effectively disabled
   or every stalled slot is output-fresh-and-cannot-be-reclaimed.
   `test_halt_stalled_still_reachable_when_reclaim_disabled` proves the verdict is
   still `HALT:stalled` when `stall_reclaim_minutes` is set beyond reach.

2. **Shell parity — OK.** FR-74 lives in the shared stall branch (keyed on heartbeat
   age + output age), so it applies to shell dispatch too
   (`test_shell_mode_stall_also_reclaims`). The FR-72 shell launch-fail path (claimed
   + no heartbeat past grace → `auth_or_launch_failed`) is untouched.

3. **FR-72 launch path unchanged — OK.** The reclaim is added only to the
   `if has_any:` stall branch; the FR-72 `if state == "claimed" and not has_any`
   advisory/hard-cap path is byte-for-byte unchanged. The full `test_subagent_liveness.py`
   (16 tests) stays green.

4. **CANCEL / no-double-dispatch — OK.** `_ctl_cancel` is untouched and reuses the
   same `_synthesize_failure` path FR-74 reuses; no requeue is implemented (FR-74
   abandons only), so there is no double-dispatch surface.

5. **OUT-AGE display-only — OK.** The column is added in `_format_table` only. Doneness
   (`_terminal_status_of`) and dispatch are untouched; the FR-74 guard reads the
   `_output_age_secs` data signal directly, never the rendered string
   (`test_out_age_is_display_only_not_lifecycle`).

6. **stdlib-only / bounded — OK.** No new imports; `os.walk`/`os.stat`/`Path.glob`
   only. The scan is file-count-capped (`_OUTAGE_FILE_CAP`) and VCS-pruned
   (`test_outage_scan_is_bounded`, `test_vcs_dirs_pruned`). NFR-3 intact.

### Round-1 FIX-REQUIRED (B-F1) — per-render scan cost at batch scale

`_format_table` iterated **every** run and ran the bounded OUT-AGE scan for each —
including queued (not-yet-started) and terminal (accumulated) runs. For a 58-job
batch, a `monitor` refresh would do up to N bounded walks; on a default whole-tree
scan over a `node_modules`-heavy repo that is a real cost multiplier. The instruction
requires "never a full recursive walk per render"; per-run it is bounded, but
aggregate cost grows O(all runs), not O(active runs).

**FIX (applied):** `_format_table` now computes OUT-AGE only when
`st in _INFLIGHT_STATES` (claimed/running/stalled); queued and terminal runs render
`-`. OUT-AGE answers "is this live worker still producing?" — only actionable for an
in-flight run — so this is also semantically tighter. Per-render cost is now bounded
by ~`pool_size`, not the accumulated run count. The engine reclaim path already only
scans *stalled* runs. Display tests (`test_monitor`/`test_tui`/`test_display_reconcile`,
77 with the FR-74/73 set) stay green after the fix.

## Round 2 — verdict

B-F1 fixed and re-verified; full suite 483 green post-fix. No regression to FR-72,
CANCEL, shell parity, doneness, or renderer parity.

**SHIP.**
