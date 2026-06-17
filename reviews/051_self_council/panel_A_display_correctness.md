# Panel A — display correctness (round 1)

**VERDICT: SHIP**

## Confirmed correct
- `_reconcile_state` is a pure function (no I/O; caller supplies the heartbeat observation).
  - Terminal sentinel over an in-flight persisted state → terminal truth + `*` (monotonic; correctly ignores mtime age).
  - Fresh IN_PROGRESS/STARTING over `claimed` → `running*`, gated by `(now - hb_mtime) <= fresh_secs`.
  - **Stale IN_PROGRESS from a dead worker over `claimed` correctly stays `claimed`** — the freshness guard works; no "dead worker shown as running" failure introduced.
  - `stalled` + fresh IN_PROGRESS → stays `stalled` (the running rule intentionally matches only `claimed`; engine recovery of `stalled`→`running` stays the tick's job). Conservative and safe.
- **Display-only / FR-18 preserved.** Called only from display paths (`_format_table`, `data.entry_detail`, `data.run_health`); no engine/reaping caller. Doneness still sourced from the worker's status field via `_advance`.
- **STALE-TICK cadence source sound & consistent.** Both `cli._monitor_freshness_line` and `data.run_health` use `2 * next_tick_minutes * 60`, guarded by isinstance + `> 0`; garbage/absent → no false STALE; `done` excluded.
- **Column width.** STATE is `%-13s`, labels truncated `[:12]`: `completed*`/`abandoned*`(10), `running*`(8), `LAUNCH-FAIL`(11) all fit. `*` legend appended when any live; monitor line also carries it.

## NITs (addressed after round 1)
- **N1 — stale-IN_PROGRESS-stays-claimed guard untested.** Added `test_stale_inprogress_stays_claimed`.
- **N2 — engine/display terminal-detection asymmetry.** Display read only the LAST heartbeat line (`_hb_observe`) while the engine scans the whole tail (`_terminal_status_of`); a non-terminal line trailing a terminal sentinel would fail to reconcile to `completed*` (fails safe to old behavior, but exactly in the targeted window). Fixed: display paths now compute `eff = _terminal_status_of(hb) or hb_status`. Added `test_terminal_sentinel_trailing_line`.
- OK-with-note: footer counts stay persisted (honest tally) while a row may show `completed*` — mitigated by the `*` legend.
