# Instruction 011 — harden the fragile `test_format_picker_row` (temp-dir isolation)

## What this is
Orchestrator floor verification (Cowork, **Python 3.10.12**, full suite on `fr75-retry`) found **one failure the worker's 3.14.6 run did not**: `tests/test_tui.py::DataLayerViewModels::test_format_picker_row_live_and_done` — expected `DONE`, got `DEAD` (`506 passed, 1 failed`). It is **NOT an FR-75 defect** — FR-75 never touched the TUI, and the test **passes in isolation (3×)** and on the worker's clean 3.14.6 env (×3). It is a **pre-existing fragile test** that FR-75's +12 new tests tipped over by leaving more run-dirs in the shared system temp dir.

**Root cause (confirmed):** the test does
```python
rd = _run_dir(done=True)                 # no root -> tempfile.mkdtemp() in the SHARED /tmp
run = DATA.list_runs(rd.parent)[0]       # rd.parent == /tmp -> lists EVERY run-dir in /tmp, newest-first
```
`list_runs` returns every run-dir under the given root, newest-first, so `[0]` can be a **leaked run-dir from another test** (the failure picked up a `Q1 R1 C0 F0` in-progress, stale → `DEAD` run that isn't even this test's `done` run). The fixture already supports an isolated parent via its `root=` param (see `_run_dir` def + the sibling tests that pass `root = Path(tempfile.mkdtemp())`).

**You cannot reproduce this on 3.14.6** (the temp-dir contents differ / the test passes there) — fix it **by construction** (give the test its own parent dir so `list_runs` only ever sees its one run). The **orchestrator re-verifies the full floor suite green** as the hard gate.

## Prerequisite / branch (do NOT land)
On the **existing** `fr75-retry` branch, worktree `~/Documents/arunner-fr75`, on top of 010's commits (`c3c80cd` + `e3d666c`). **Pre-flight:** `git -C ~/Documents/arunner-fr75 rev-parse --abbrev-ref HEAD` → `fr75-retry`; if the worktree is gone, `git worktree add ~/Documents/arunner-fr75 fr75-retry`. **Do NOT merge/land** — the operator lands `fr75` after the orchestrator's floor re-verify.

## The fix (test-only — do NOT touch `arunner/tui/` source)
1. In `test_format_picker_row_live_and_done`, give the run an **isolated parent**:
   ```python
   root = Path(tempfile.mkdtemp())
   rd = _run_dir(done=True, root=root)
   run = DATA.list_runs(root)[0]        # isolated -> only this run
   ```
   (`rd.parent == root` now, so `list_runs(root)` returns exactly the test's own run.)
2. **Audit `tests/test_tui.py`** for any OTHER `DATA.list_runs(...)` whose root is a *shared* temp parent (e.g. an unrooted `_run_dir(...).parent`), and isolate those the same way. Leave the ones that already pass an explicit `root` alone.
3. **Do not change any `arunner/` source** — the TUI behavior is correct; only the test's setup is fragile. (If you believe a source change is warranted, STOP and write `pre-flight-aborted` with the rationale rather than editing source.)

## Tests
- The target test must pass and be **immune to temp-dir contents** (its `list_runs` sees only its own run).
- Full suite `python3 -m pytest tests/ -q` green. Since the bug doesn't manifest on your 3.14.6, run the suite **a few times** and confirm stable green; the **orchestrator's hard gate is the full floor suite on Python 3.10.12, robustly green across repeated runs**. Report your Python version + counts. stdlib-only (NFR-3); test-only change.

## Council
Single-panel self-Council (tiny, deterministic test-isolation fix), charter: (a) the test now uses an isolated parent and no longer reads the shared system temp dir; (b) **no `arunner/` source touched** (`git diff --name-only` shows only `tests/test_tui.py`); (c) no other fragile `list_runs(shared-parent)` left in `test_tui.py`. Write `runner/reviews/011_self_council/`. Iterate to SHIP.

## §9 / requirements
None — test-only hygiene fix, no FR/US/UC/§9 change. (Optionally note in the output that it hardens a pre-existing fragile test surfaced during FR-75 floor verification.)

## Commit / output
Focused commit on `fr75-retry` (do NOT push/merge — operator lands `fr75` after the orchestrator's floor re-verify). Output → `outputs/011-tui-test-isolation.md`: the before/after of the test, the audit result (any other tests isolated), confirmation that `git diff` touched only `tests/test_tui.py`, suite counts + your Python version + how many repeats you ran, the single-panel verdict, `git log --oneline -3`.
