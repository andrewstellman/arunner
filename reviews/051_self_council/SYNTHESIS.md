# Instruction 051 — 3-panel self-Council synthesis

**Subject:** display-correctness reconciliation (monitor + tui) + TUI Phase-2 (overview / kill / clipboard) + the FR-62 TUI Council instr 050 left undone.

**Outcome: unanimous SHIP** (Panel A round 1; Panels B & C round 2 after fixing two blockers).

## Panels & charters
- **A — display correctness:** reconciliation shows live truth; tick-age vs heartbeat-liveness always distinguishable; no new way to mislead.
- **B — read-only-safety boundary:** only the kill action writes (confined + confirmed); monitor/overview/copy/tail never write; renderer still shared, not forked.
- **C — feature + regression:** overview health-flags correct; kill wires the real CANCEL/STOP verbs; clipboard stdlib/degrades; no engine dependency added; existing tests still pass.

## Round 1
- **Panel A → SHIP.** Core reconciliation correct and pure; display-only (FR-18 preserved); STALE-TICK cadence source sound; column widths fit. NITs: (1) stale-IN_PROGRESS-stays-claimed guard untested; (2) engine/display asymmetry — display read only the LAST heartbeat line (`_hb_observe`) while the engine scans the whole tail (`_terminal_status_of`), so a non-terminal line trailing a terminal sentinel would fail to reconcile to `completed*`.
- **Panel B → FIX-REQUIRED (BLOCKING).** The load-bearing never-writes pin `tests/test_tui.py::test_never_writes` snapshotted `rd.parent`, which was the shared system temp dir (`rd = mkdtemp()` → `rd.parent == gettempdir()`), so it failed non-deterministically (reproduced FAIL/FAIL/FAIL/OK) and could not reliably bite a real write regression. The boundary property itself held; the broken pin was the blocker. (Pre-existing from instr 050, but it guards exactly the boundary this change relaxes, so fixing it is in scope.)
- **Panel C → FIX-REQUIRED (BLOCKING).** `run_health` HUNG? was computed from heartbeat-mtime absence only, never consulting `claimed_at` — so it false-flagged **every** freshly-claimed-but-not-yet-heartbeating entry as HUNG during its normal launch window, contradicting both the charter ("past launch grace") and the engine's own launch-fail model (`(now - claimed_at) > grace_secs`). The existing HUNG? test was claimed_at-blind. Other items (kill verbs, clipboard, no-engine-dep, regression) OK. Suite 375, 3× OK.

## Fixes applied (commit after round 1)
1. **HUNG? gates on `claimed_at` past grace** (Panel C blocker) — `run_health` now flags HUNG? only when `claimed_at` is numeric AND `(now - claimed_at) > grace_secs`, after a whole-tail terminal skip and a fresh-heartbeat skip. Mirrors the engine `_advance` horizon. Tests: `test_recent_claim_not_hung` (RUNNING), `test_claimed_past_grace_no_heartbeat_is_hung` (HUNG?).
2. **Never-writes pin scoped to a dedicated root** (Panel B blocker) — `_run_dir(root=...)` + `test_never_writes` build the fixture under a fresh `mkdtemp()` so the runs-root snapshot can't be polluted by other processes. Now deterministic (8/8 OK) and still bites (run-dir subtree hash + dedicated-root + control/lock checks).
3. **Engine/display terminal detection aligned** (Panel A NIT) — `_format_table` and `entry_detail` and `run_health` now use `_terminal_status_of(hb)` (whole-tail scan, matches the engine) for the terminal-ahead case, so a trailing non-terminal line can't hide a completion. Test: `test_terminal_sentinel_trailing_line`.
4. **Stale-guard pinned** (Panel A NIT) — `test_stale_inprogress_stays_claimed`: an ancient IN_PROGRESS over `claimed` stays `claimed`, never false `running*`.

## Round 2
- **Panel B → SHIP.** Blocker resolved; pin now isolated + deterministic (8/8) and strictly stronger; other OK findings re-confirmed (single write path, confirm-gated kill, shared renderer).
- **Panel C → SHIP.** HUNG? fix mirrors the engine horizon exactly; new tests cover both directions; priority order intact; clipboard/no-dep/no-engine-change re-confirmed. Suite 379, OK.

## Evidence
- Suite **375 → 379**, 3× stable (Python 3.14.5).
- Kill flow proven end-to-end through the real Textual pilot (`k` → ConfirmScreen → `y` → `CANCEL` written with body `run-01`).
- Reconciliation before/after captured in the output doc.
- Strictly read-only except the one confirm-prompted kill control write (mutation-pinned: `only-kill-writes`).
