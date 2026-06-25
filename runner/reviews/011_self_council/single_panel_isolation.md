# Single-panel self-Council — instr 011 (test-isolation hardening)

**Scope:** a test-only hygiene fix — harden the fragile
`tests/test_tui.py::DataLayerViewModels::test_format_picker_row_live_and_done`
(surfaced by Cowork's Python-3.10.12 floor verify of `fr75-retry`: 506 passed,
1 failed; the test expected `DONE`, got `DEAD`). Not an FR-75 defect — FR-75 never
touched the TUI; its +12 new tests merely left more run-dirs in the shared system
temp dir, tipping over a pre-existing fragile test.

## Charter checks

**(a) The test uses an isolated parent and no longer reads the shared system temp
dir. — PASS.**
Before:
```python
rd = _run_dir(done=True)                 # unrooted -> mkdtemp() in shared /tmp
run = DATA.list_runs(rd.parent)[0]       # rd.parent == /tmp -> newest of EVERY /tmp run-dir
```
After:
```python
root = Path(tempfile.mkdtemp())
rd = _run_dir(done=True, root=root)       # rd is created UNDER root
run = DATA.list_runs(root)[0]             # isolated -> only this run
```
`list_runs(root)` now sees exactly the test's own run (the `_run_dir` fixture's
`root=` param places `rd` under `root`, so `rd.parent == root`). The picker row is
read off this run's own `done` status, immune to whatever else lives in `/tmp`.
**Verified by construction + empirically:** the target test passes ×5 standalone,
and passes when run immediately after all 42 FR-75 `test_run_robustness.py` tests
(which leak run-dirs into `/tmp`) — order-independent (43 passed).

**(b) No `arunner/` source touched. — PASS.**
`git diff --name-only` → `tests/test_tui.py` (only). The TUI behavior is correct;
`list_runs` returning every run-dir under its given root, newest-first, is the
documented contract — the bug was the test handing it the shared `/tmp` as the
root. No source change is warranted (no STOP/pre-flight-abort needed).

**(c) No other fragile `list_runs(shared-parent)` left in `test_tui.py`. — PASS.**
Audited all five `DATA.list_runs(...)` call sites:
| line | call | root | verdict |
|---|---|---|---|
| 122 | `list_runs(root)` | `root = mkdtemp()`, `rd` rooted under it | isolated — OK |
| 141 | `list_runs(missing)` | `mkdtemp()/"nope"` (non-existent) | isolated — OK |
| 244 | `list_runs(root)` | `root = mkdtemp()`, run-a/run-b created under `root` | isolated — OK |
| 254 | `list_runs(root)` | `root = mkdtemp()`, `broken/` under `root` | isolated — OK |
| ~298 | `list_runs(rd.parent)` | unrooted `_run_dir().parent` == shared `/tmp` | **was fragile → FIXED** |
Only line ~298 read a shared parent; it is now isolated. The other four already
pass an explicit dedicated `root` and are left unchanged.

## Evidence
- Full suite `python3 -m pytest tests/ -q`: **506 passed, 1 skipped ×3**,
  Python **3.14.6**. Target test ×5 green; `test_tui.py` whole-file ×2 green;
  order-independence run (FR-75 robustness tests + target) green.
- The bug does NOT manifest on 3.14.6 (temp-dir contents differ); the fix is
  **by construction** (isolated parent). The orchestrator's hard gate remains the
  full floor suite on Python 3.10.12, robustly green across repeated runs.
- stdlib-only (NFR-3); test-only change. No FR/US/UC/§9 change.

## Verdict: **SHIP.** Isolated parent, no source touched, no other fragile
`list_runs(shared-parent)` remaining.
