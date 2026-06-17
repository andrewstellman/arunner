# Instruction 050 self-council synthesis — FR-62 interactive read-only Textual TUI (`arunner tui`)

*Mandatory 3-panel. Three fresh-context, role-locked, adversarial reviewers
verifying on disk: tracing every TUI code path for a write and biting the
never-writes pin (mutation-verified); confirming the run-view table is the FR-59
renderer reused, not forked, and that the test pins the shared call path; and
proving Textual is gated behind the `[tui]` extra with zero leakage onto the
stdlib engine path (subprocess import-graph check, with Textual actually
installed so the pass is real). Date: 2026-06-17.*

| Panelist | Charter | Verdict |
|----------|---------|---------|
| `panelist_A_read_only_safety.md` | the TUI cannot write/lock/advance under any path; never-writes pin bites a mutation; same property as FR-59 | **SHIP** |
| `panelist_B_renderer_reuse_no_fork.md` | the run-view table IS `cli.render_monitor_frame`→`_format_table` (no copy); the test pins the shared call path; the TUI can't drift from `monitor` | **SHIP** |
| `panelist_C_packaging_decoupling.md` | Textual gated behind `[tui]`; bare engine install dependency-free and importable without Textual; `monitor` still the zero-dep fallback; clean degradation | **SHIP** |

## Outcome: unanimous SHIP (round 1)

### Panelist A — read-only safety (SHIP)
The data layer (`arunner/tui/data.py`) performs only reads; a package-wide grep
for `mkdir|open(...,'w'/'a')|write*|touch|unlink|rename` hits only docstrings.
`list_runs` returns `[]` on a missing runs-root **without creating it**. The view
layer (`app.py`) calls only DATA reads + in-memory Textual ops; no
screenshot/log/state write to the run-dir or cwd. Every delegated engine helper
(`render_monitor_frame`, `_format_table`, `_hb_observe`, `_heartbeat_path`,
`_read_result_record`) is read/stat only; the `_TickLock` writer and
`_write_summary` are never on a TUI-reachable path. The never-writes pin
snapshots BOTH the run-dir and the runs-root and drives the full read surface
over 3 passes; **injecting a stray write into `list_runs` turned it RED**, then
restored byte-identical with all 17 tests green.

### Panelist B — renderer-reuse-no-fork (SHIP)
`run_view_frame` is a one-line delegate to `CLI.render_monitor_frame` — the same
function `cmd_monitor` calls — so the TUI and `monitor` execute byte-identical
code for the table body + freshness header. No status-table layout exists
anywhere in `arunner/tui/`; the new formatters (`format_entry_detail`,
`format_picker_row`, `format_history`) render *different* data (per-entry record,
run summary, heartbeat lines), never the status table. The test has both the
`endswith(_format_table(...))` equality pin AND a monkeypatch call-count pin
(`render_monitor_frame` invoked exactly once) — stronger than `test_monitor.py`'s
string-only pin, and it closes the "copy that happens to match" gap. A fork would
fail one or both tests.

### Panelist C — packaging & decoupling (SHIP)
With **Textual 8.2.7 actually installed**, importing `arunner.cli` +
`arunner.engine.tick` + `arunner.tui.data` still leaves `'textual' not in
sys.modules` — proving lazy decoupling, not an absent-dependency false pass.
`pyproject.toml` declares the `tui` extra and ships `arunner.tui` in the wheel;
the base project has no Textual. Textual is imported only in `app.py`, reached
only via the lazy import inside `cmd_tui`; `_DISPATCH` holds the function object,
so `--help`/parser build stay Textual-free. `cmd_tui` degrades on `ImportError`
with the install hint + the `monitor` fallback pointer, exit code 3. The engine
package has zero `textual` references. `arunner monitor` is unchanged and remains
the zero-dependency fallback.

## Disposition
No blocking findings from any panel; no iteration required. The four read-only
views (run picker → live run-view table → entry detail → log/heartbeat tail) are
built on a stdlib, never-writes data layer that reuses the FR-59 render path, and
the Textual dependency is gated and decoupled so it never touches the engine.
Full suite: **351 passed**, run 3×, Python 3.14.5.

**SHIP.**
