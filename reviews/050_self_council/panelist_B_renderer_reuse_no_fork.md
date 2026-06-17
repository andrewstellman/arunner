# Panelist B — renderer-reuse-no-fork (FR-62 Textual TUI)

**Charter:** the TUI's run-view table must BE the FR-59 monitor's renderer, not a
copy, so the TUI can never drift from `arunner monitor`.

**Verification performed:** read `arunner/tui/data.py`, `arunner/tui/app.py`,
`cli.render_monitor_frame`/`_monitor_freshness_line`/`cmd_monitor`,
`tick._format_table`; grepped all of `arunner/tui/` for any status-table layout,
freshness line, or HB-age formatting; compared the renderer-reuse pins in
`test_tui.py` vs `test_monitor.py`.

## Findings (all non-blocking, PASS)

1. **Delegation is real, single-line, no fork.** `data.py` `run_view_frame` is a
   one-line delegate: `return CLI.render_monitor_frame(Path(run_dir),
   interval=interval, now=now)`. It loads no status/plan and formats nothing.
   `render_monitor_frame` is the same function `cmd_monitor` calls; it builds the
   frame from `TICK._format_table(...)` plus the monitor-owned
   `_monitor_freshness_line`. The TUI and `arunner monitor` therefore execute
   byte-identical code for the table body and freshness header.

2. **No forked/copied renderer in `arunner/tui/`.** Grep for the table's
   distinguishing tokens (`_format_table`, the `RUN/REPO/MODE/HB-AGE` header,
   `%-5s`/`%-22s` column fmt, `monitor: refresh`, `Queue:`, `Next tick`,
   `_hb_age`) finds zero status-table layout in the TUI package. The only `%-22s`
   occurrences are in `format_picker_row` (a per-run summary view-model), not the
   status table.

3. **New formatters render different data, not the status table.**
   `format_entry_detail` renders one per-entry record; `format_picker_row` a run
   summary line; `format_history` heartbeat/journal lines. None emit the
   RUN/REPO/MODE/STATE/ACTIVITY/LAST-HB/HB-AGE table. `RunViewScreen._refresh_table`
   gets its text solely from `DATA.run_view_frame` — the only table source in the
   UI.

4. **The test pins the shared CALL PATH, mirroring `test_monitor.py`.**
   `test_run_view_reuses_renderer_no_fork` asserts `text.endswith(_format_table(...))`
   + the freshness header (identical shape to `test_monitor.py`).
   `test_run_view_delegates_to_monitor_call_path` monkeypatches
   `CLI.render_monitor_frame` and asserts it was invoked **exactly once** — the
   call-path proof, *stronger* than `test_monitor.py`'s string-only pin.

## Drift-risk analysis
A silent fork would require either (a) `run_view_frame` to stop calling
`render_monitor_frame` — caught by the call-count test (would drop to 0) — or (b)
the table body to be reformatted — caught by the `endswith(_format_table(...))`
pin. No path in `app.py` renders a table outside `run_view_frame`. No residual
drift risk.

VERDICT: SHIP
