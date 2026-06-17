# Panel B — read-only-safety boundary

## Round 1 — VERDICT: FIX-REQUIRED
The boundary property itself HELD, but the load-bearing safety pin was broken:

- **OK — single write path.** `DATA.write_kill_control` is the ONLY write path in the whole TUI + data layer (mutation grep over `arunner/tui/` returns only its two `write_text` lines). app.py has zero direct fs writes. The data layer calls only engine *readers*. `list_runs` does not create a missing root; `run_health`/`run_view_frame`/`entry_detail` are read-only.
- **OK — write_kill_control confined + correct.** STOP → empty `STOP` (matches `cli.py` + the engine `.exists()` gate); CANCEL → `CANCEL` with the run id in the body (matches `_read_control_value` + `_parse_run_id`). CANCEL with no run id raises before any write; unknown verb rejected.
- **OK — kill always confirm-gated; clipboard touches only the paste buffer.** `action_kill` only pushes `ConfirmScreen`; the write lives in a `_do` closure invoked solely by `ConfirmScreen.action_yes` on explicit `y`. `copy_to_clipboard` shells out via subprocess stdin, never the run-dir.
- **OK — renderer shared, not forked.** `run_view_frame` → `CLI.render_monitor_frame` → `TICK._format_table`; reconciliation lives in the shared `_format_table`.
- **BLOCKING — the legacy never-writes pin is flaky.** `tests/test_tui.py::test_never_writes` snapshotted `root = rd.parent`, and `rd = mkdtemp()` → `rd.parent == gettempdir()`, so it diffed the entire system temp dir; unrelated temp files made it fail non-deterministically (reproduced FAIL/FAIL/FAIL/OK). A load-bearing safety pin that throws false positives can't be trusted to bite a real regression. Fix: scope the snapshot to a dedicated root.

## Round 2 — VERDICT: SHIP
- Blocker RESOLVED: `_run_dir(root=)` uses `tempfile.mkdtemp(dir=root)`; `test_never_writes` builds the fixture under a dedicated `root = mkdtemp()` so `rd.parent == root` is isolated.
- Pin still BITES: full run-dir subtree snapshot (mtime_ns/size/hash) + dedicated-root tree + `.tick.lock`/control-file checks — a write into the run-dir or a dropped control file still FAILS.
- Determinism: 8/8 OK via `discover -p test_tui.py`.
- Other round-1 OK findings re-confirmed; `test_display_reconcile.py::test_views_never_write_only_kill_does` correctly scoped to `rd`.
