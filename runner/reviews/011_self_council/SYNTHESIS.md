# Self-Council SYNTHESIS — instr 011 (test-isolation hardening)

**Verdict: SHIP** (single-panel self-Council; no FIX needed — the fix matched the
instruction exactly and all three charter checks pass on first review).

## Panel
- **Single panel (test-isolation): SHIP.** See `single_panel_isolation.md`.
  - (a) `test_format_picker_row_live_and_done` now builds its run under a
    dedicated `root = mkdtemp()` and calls `list_runs(root)` — immune to shared
    `/tmp` contents (verified ×5 + order-independent against the FR-75 run-dir
    leakers).
  - (b) No `arunner/` source touched — `git diff --name-only` = `tests/test_tui.py`.
  - (c) Audited all five `list_runs(...)` sites; only the target read a shared
    parent. The other four already isolate. Nothing else fragile.

## Evidence
- Full suite: **506 passed, 1 skipped ×3**, Python **3.14.6**. Target test ×5 +
  order-independence run + `test_tui.py` ×2: all green.
- test-only, stdlib-only (NFR-3); no FR/US/UC/§9 change.
- Hard gate remains the orchestrator's Python-3.10.12 full-floor re-verify
  (robustly green across repeated runs).
