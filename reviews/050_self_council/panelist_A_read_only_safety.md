# Panelist A — read-only safety (FR-62 Textual TUI)

**Charter:** the TUI NEVER writes — no run-state write, no `.tick.lock`, no control
file, no tick — the same load-bearing property FR-59's monitor holds. The
never-writes pin must bite a mutation.

**Verification performed:** read `arunner/tui/data.py`, `arunner/tui/app.py`,
`cli.cmd_tui`, `tests/test_tui.py`; traced every delegated engine/CLI helper to
disk; grepped the TUI package for filesystem-mutating calls; mutation-tested the
pin.

## Findings (all non-blocking, confirmed-clean)

1. **Data layer is strictly read-only.** Every `arunner/tui/data.py` function
   performs only reads: `_read_json` (read_text, swallows OSError/ValueError →
   None), `list_runs` (`iterdir`/`is_file`/`stat`/read; returns `[]` on a missing
   root **without creating it**), `run_view_frame` (delegates to
   `CLI.render_monitor_frame`), `entry_detail`, `heartbeat_history`,
   `journal_tail`, `tail_lines` (read with `errors="replace"`, missing → `[]`).
   Grep for `mkdir|open(...,'w'/'a')|write*|touch|unlink|rename|makedirs` hits
   only docstrings. No mutating call.

2. **View layer holds no write path.** `app.py` `on_mount`/`set_interval`/
   `action_*`/bindings call only DATA reads and in-memory Textual ops
   (`Static.update`, `ListView.clear/append`, `push_screen`). No screenshot/log/
   CSS-file output; `App.run()` touches at most Textual's own config dir, never
   the run-dir or cwd.

3. **Delegated engine/CLI helpers are read-only.** `cli.render_monitor_frame`
   reads `harness_status.json`/`plan.json` + a `STOP`-existence check; no write.
   `tick._format_table` → `_hb_observe`/`_heartbeat_path`/`_hb_age_str`/
   `_ascii_trunc`/`_next_cadence` — all read/stat only. `_read_result_record`
   reads + swallows. The `_TickLock` writer and `_write_summary` exist in the
   engine but are **never** on any TUI-reachable call path.

4. **`cmd_tui` takes no lock and writes nothing** — resolves the run-dir, probes
   `harness_status.json` (read), lazily imports the app, launches. No control-file
   drop, no lock, no tick.

5. **The never-writes pin is a REAL mutation pin.** `NeverWrites::test_never_writes`
   snapshots both the run-dir (content-hash + mtime + size) AND the runs-root
   (full `rglob`), drives the *entire* read surface over 3 passes, then asserts no
   run-dir mutation, no runs-root file add/remove, no `.tick.lock`, no
   STOP/PAUSE/RESUME/CANCEL/POOL/CADENCE/POLL-NOW. `test_list_runs_does_not_create_missing_root`
   pins the no-create-root path. **Mutation-verified:** injecting
   `(root/"_MUTATION_PROBE").write_text("x")` into `list_runs` turned the pin RED
   on the runs-root assertion; restored byte-identical, all 17 tests green.

No hidden write path found.

VERDICT: SHIP
