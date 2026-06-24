# Instruction 005 — FR-72 subagent-mode liveness — 3-panel self-Council synthesis

**Verdict: UNANIMOUS SHIP** (commit `366a5bd` on `fr72-subagent-liveness`, base `main`/6ac47ef).

Re-derivation of the (stale, pre-format-collapse) subagent-liveness feature onto
the unified one-format engine on `main`. Renumbered FR-72 / US-18 / UC-14.

## Panels & charters
- **A — correctness/spec:** the three layers match FR-72 on the new engine; advisory non-terminal + slot-held; cap reclaims; STARTING only for subagent.
- **B — regression-safety:** shell-mode parity preserved; no false-`done`; advisory display composes with the instr-051 reconcile/tokens render; `auth_or_launch_failed` stays reachable exactly where the engine has authority.
- **C — test sufficiency/honesty:** 10 pins ported + bite (mutation-verified); FR-72/US-18/UC-14 added with no number reuse; §9 honest.

## Round 1 — B SHIP, C SHIP, A FIX-REQUIRED (4 findings)
B and C returned **SHIP** with full evidence (B: shell parity intact, no false-done, display composition sound, checker still catches real double-dispatch, re-aimed tests not weakened; C: all 10 pins bite, load-bearing pin mutation-verified, docs honest, no number reuse, 457 green). Both flagged the same gap A raised.

Panel A returned **FIX-REQUIRED**: the ownership fork + STARTING-emit were applied ONLY to the single-prompt `_advance` path, not to the other subagent-dispatch paths the same engine owns:
- **F1 (HIGH):** `_advance_multistep` — a `mode: pipeline` `agent` step still false-failed at grace (`auth_or_launch_failed`, `done=True`).
- **F2 (MEDIUM):** `_advance_judge` — a reasoning-gate judge (a pure subagent) failed-closed at grace, not at the cap.
- **F3 (MEDIUM):** Layer-B STARTING absent for multistep agent steps + judges (the instruction's concrete-changes #1 explicitly names `_dispatch_step`).
- **F4 (LOW):** no `--check` guard against `subagent_hard_cap_minutes <= launch_grace_minutes`.

## Resolution (committed in 366a5bd, additive to the round-1 code B/C reviewed)
- F1: `_advance_multistep` forks the step grace branch on `_dispatch_mode_of(step)` — agent step → NO-HEARTBEAT advisory past grace (slot held), terminal past the hard cap; shell/command/log steps keep grace-terminal parity. `_dispatch_step` emits STARTING on the step hb.
- F2: `_advance_judge` treats the judge as advisory past grace; fail-closed to `internal_error` only past the hard cap (FR-63 fail-closed preserved). `_dispatch_judge` emits STARTING on the gate hb.
- F3: covered by F1/F2 (`_emit_subagent_starting` generalized to accept the sub-run hb path).
- F4: `check_plan` rejects `subagent_hard_cap_minutes <= launch_grace_minutes`.
- New regression tests: `MultistepSubagentLivenessTests` (advisory / emits-starting / hard-cap / shell-parity) + `HardCapCheckTests`; the multistep fork is a 2nd mutation-verified pin.

## Round 2 — A SHIP
Panel A re-probed all four fixes empirically: agent step → advisory past grace / terminal past cap; shell step → grace-terminal; judge → advisory past grace / `internal_error` past cap (FR-63 contract preserved); STARTING emitted for steps + judges, not shell; `--check` rejects the bad cap. No new issue. Full suite **463 passed**.

## Final state
- **A: SHIP · B: SHIP · C: SHIP** — unanimous.
- Suite: **463 passed ×3**, Python 3.14.6. Single-prompt + multistep forks both mutation-verified to bite.
- Committed `366a5bd` on `fr72-subagent-liveness` (short-lived branch off `main`), local only — not pushed/merged.
- Process: committed BEFORE the Council (the instr-004 lesson) so a panelist's `git checkout` restores the committed file rather than reverting uncommitted work.
</content>
