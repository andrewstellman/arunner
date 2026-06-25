# Output for 011-tui-test-isolation.md
**Status:** completed

## Summary
Hardened the pre-existing fragile `tests/test_tui.py::DataLayerViewModels::test_format_picker_row_live_and_done`
by giving its run-dir an **isolated parent**, so `DATA.list_runs(...)` sees only
the test's own run. Surfaced by Cowork's **Python-3.10.12** floor verify of
`fr75-retry` (506 passed, **1 failed** — expected `DONE`, got `DEAD`); it is **not
an FR-75 defect** (FR-75 never touched the TUI). FR-75's +12 new tests merely left
more run-dirs in the shared system temp dir, tipping the fragile test over.
**Test-only change; no `arunner/` source touched.** Single-panel self-Council: SHIP.

## Before / after
**Before** (lines ~297-299):
```python
def test_format_picker_row_live_and_done(self):
    rd = _run_dir(done=True)                 # unrooted -> mkdtemp() in the SHARED /tmp
    run = DATA.list_runs(rd.parent)[0]       # rd.parent == /tmp -> newest of EVERY /tmp run-dir
    self.assertIn("DONE", DATA.format_picker_row(run))
```
`list_runs` returns every run-dir under its root, newest-first; `[0]` could be a
leaked run-dir from another test (the 3.10.12 failure picked up a stale
in-progress `Q1 R1 C0 F0` run → `DEAD`, not this test's `done` run).

**After:**
```python
def test_format_picker_row_live_and_done(self):
    # Isolated parent so list_runs() sees ONLY this run ...
    root = Path(tempfile.mkdtemp())
    rd = _run_dir(done=True, root=root)
    run = DATA.list_runs(root)[0]            # isolated -> only this run
    self.assertIn("DONE", DATA.format_picker_row(run))
```
`rd.parent == root` now, so `list_runs(root)` returns exactly the test's own run —
immune to `/tmp` contents **by construction**. The `_run_dir` fixture already
supports `root=` (used by the sibling isolated tests).

## Audit result (instruction step 2)
All five `DATA.list_runs(...)` call sites in `tests/test_tui.py`:
| line | call | root | verdict |
|---|---|---|---|
| 122 (`test_never_writes`) | `list_runs(root)` | `root = mkdtemp()`, `rd` rooted under it | isolated — OK, unchanged |
| 141 (`test_list_runs_does_not_create_missing_root`) | `list_runs(missing)` | `mkdtemp()/"nope"` (non-existent) | isolated — OK, unchanged |
| 244 (`test_list_runs_newest_first_with_summary`) | `list_runs(root)` | `root = mkdtemp()`, run-a/run-b created under `root` | isolated — OK, unchanged |
| 254 (`test_list_runs_surfaces_unreadable_status`) | `list_runs(root)` | `root = mkdtemp()`, `broken/` under `root` | isolated — OK, unchanged |
| ~298 (`test_format_picker_row_live_and_done`) | `list_runs(rd.parent)` | unrooted `_run_dir().parent` == shared `/tmp` | **was fragile → FIXED** |

Only line ~298 read a shared parent. The other four already pass an explicit
dedicated `root` and were left unchanged. No other fragile `list_runs(shared-parent)`
remains in `test_tui.py`.

## `git diff` scope
`git diff --name-only` (working changes) → **`tests/test_tui.py`** only. No
`arunner/` source touched (the TUI behavior is correct — `list_runs` returning
every run-dir under its given root newest-first is the documented contract; the
bug was the test handing it the shared `/tmp`).

## Files changed
| Path | Note |
|------|------|
| `tests/test_tui.py` | the target test now builds its run under a dedicated `root` and calls `list_runs(root)` |
| `runner/reviews/011_self_council/{single_panel_isolation,SYNTHESIS}.md` | single-panel self-Council |

## Commit (branch `fr75-retry`, local only — NOT pushed/merged)
- **`47377e9`** — test: isolate `test_format_picker_row_live_and_done` from shared temp dir (instr 011).

On top of 010's `c3c80cd` + `e3d666c`. Worktree `~/Documents/arunner-fr75`, branch `fr75-retry`.

## Tests
Full suite `python3 -m pytest tests/ -q`: **506 passed, 1 skipped — ×3 stable
green**, Python **3.14.6**. Additional robustness runs:
- target test ×5 standalone — green each time;
- target test run immediately after all 42 `test_run_robustness.py` tests (which
  leak run-dirs into `/tmp`) — **43 passed**, order-independent;
- `test_tui.py` whole-file ×2 — 17 passed each.

The bug does NOT manifest on 3.14.6 (the temp-dir contents differ / the test
passes there), so the fix is **by construction** (isolated parent). The
orchestrator's hard gate is the full floor suite on **Python 3.10.12**, robustly
green across repeated runs.

## Council
**Single-panel self-Council: SHIP** — `runner/reviews/011_self_council/SYNTHESIS.md`.
No FIX needed — all three charter checks pass on first review: (a) isolated parent,
no shared-temp read; (b) no `arunner/` source touched (`git diff --name-only` =
`tests/test_tui.py`); (c) no other fragile `list_runs(shared-parent)` in the file.

## §9 rows flipped
None — test-only hygiene fix, no FR/US/UC/§9 change. Hardens a pre-existing
fragile test surfaced during FR-75 floor verification (the floor failure was the
test's setup, not the FR-75 engine change).

## Notable observations
- The fix is **by construction** (isolated parent), not a re-tuning of the 3.14.6
  run — the worker's interpreter can't reproduce the shared-`/tmp` ordering that
  triggers it, so the orchestrator's 3.10.12 full-floor re-verify is the standing
  hard gate (same pattern as the instr-007 portability lesson).
- The root cause is shared-mutable-state-in-`/tmp` test fragility, independent of
  FR-75; FR-75's extra run-dirs were the trigger, not the cause.

## Next action expected from orchestrator
Re-verify the full floor suite on Python 3.10.12 (robustly green across repeated
runs) as the hard gate, then land `fr75-retry` (`c3c80cd` + `e3d666c` + `47377e9`)
on `main` (operator merges; the worker does not push/merge). Per
`docs/PLANNED_run_robustness.md` §8, the remaining 1.1.0 single-trunk step is
**FR-77** (supervised-bounded model; host-capability probe first), then doc-sync;
tag `v1.1.0` when complete.
