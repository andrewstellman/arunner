# Output for 005-fr72-subagent-liveness-rederive.md
**Status:** completed

Re-derived the subagent-mode liveness feature **fresh on `main`** (post-format-
collapse engine) as **FR-72 / US-18 / UC-14** — the stale `fr-61-subagent-liveness`
branch was the spec-only reference (it collides with the rewritten engine and
reused now-shipped FR-61/US-17 numbers; NOT merged). Short-lived branch
`fr72-subagent-liveness` off `main`, one commit `366a5bd`, local only — **not
pushed/merged**. Suite **463 passed ×3**, Python 3.14.6. 3-panel self-Council:
**unanimous SHIP**.

## Before / after
**Before (`main`):** the engine's `claimed + no-heartbeat-past-launch_grace ⇒
auth_or_launch_failed` transition was unconditional — it false-failed a
`mode: agent` (subagent) worker that is alive but slow/quiet, because the engine
applied shell-mode liveness assumptions where it has no process authority (the
orchestrator's Task owns a subagent, not the engine). Observed 2026-06-17:
live workers writing full corpora marked LAUNCH-FAIL.

**After:** liveness forks by ownership on the runtime `dispatch_mode` (set from
`mode`). Shell dispatch (command/log/shell) is unchanged (the engine owns the
Popen). Subagent dispatch (mode:agent) gets the FR-40 no-false-fail invariant:
- **Layer A (advisory, not terminal):** past launch grace a subagent with no
  heartbeat raises a NON-terminal `NO-HEARTBEAT` advisory (`launch_advisory`),
  the on-disk state stays `claimed` (slot held), and it reconciles to
  `completed`/`failed` when its terminal arrives. Any heartbeat clears it.
- **Layer A' (hard cap):** `subagent_hard_cap_minutes` (plan field, default 720
  = 12h ≫ grace) reclaims a genuinely-hung silent subagent terminal — the only
  engine-side terminal reclaim for a subagent, so a hang can't pin a slot forever.
- **Layer B (lifecycle emit):** the engine writes `STARTING` on the subagent's
  behalf at dispatch (best-effort, never crashes dispatch), so `claimed→running`
  never hinges on the worker's own first heartbeat.
- **Layer C (doc-only):** TOOLKIT.md notes a subagent prompt SHOULD emit
  `STARTING` first + a terminal last.

The fork covers **every subagent the engine dispatches** — single-prompt runs,
`mode: pipeline` `agent` steps (`_advance_multistep`/`_dispatch_step`), AND
reasoning-gate judges (`_advance_judge`/`_dispatch_judge`, fail-closed to
`internal_error` only past the cap, preserving FR-63). `_format_table` overlays
the advisory + an `any_advisory` footer (composes with the instr-051
reconcile/live-marker/TOKENS render). `--check` rejects
`subagent_hard_cap_minutes <= launch_grace_minutes`.

## Files changed (8 files: +662 / −23)
| Path | Note |
|---|---|
| `arunner/engine/tick.py` | `DEFAULT_SUBAGENT_HARD_CAP_MINUTES=720` + hints/advisory-display consts; `_record_dispatch_mode_of` (run-record ownership, conservative subagent default); `_advance` subagent fork (advisory set/clear + hard-cap reclaim); `_advance_multistep` + `_advance_judge` same fork; `_emit_subagent_starting` (best-effort, hb-overridable) called on `_dispatch`/`_dispatch_step`/`_dispatch_judge` subagent paths; `_format_table` advisory overlay + `any_advisory` footer; `check_plan` cap>grace check + `subagent_hard_cap_minutes` in `_PLAN_INT_KEYS` |
| `schemas/plan.schema.json` (+ plugins copy, identical) | optional `subagent_hard_cap_minutes` (default 720); `launch_grace_minutes` desc clarified as shell-only for the terminal transition |
| `docs/REQUIREMENTS.md` | FR-72 (three layers, every-subagent-path) + US-18 + UC-14 + a VERIFIED §9 row; FR-40 lineage explicit |
| `TOOLKIT.md` | Layer-C subagent-prompt convention note |
| `tests/test_subagent_liveness.py` | the 10 reference pins ported to jobs/mode + 6 new (multistep advisory/emits-starting/hard-cap/shell-parity + cap-check) = 16 tests |
| `tests/integration/checker.py` | double-dispatch witness refined: count the engine's "dispatched to subagent" marker for subagent runs, fall back to worker STARTINGs for shell (so Layer-B's marker doesn't false-flag a single dispatch) |
| `tests/test_tick.py` | 4 pre-existing launch-fail/idempotency tests re-aimed to shell dispatch (launch-fail on grace is shell-only by design now) |

## Commits made
`366a5bd` — *FR-72: subagent-mode liveness (re-derived onto the one-format engine)* — on `fr72-subagent-liveness`, local only (one amended commit). Not pushed/merged.

## Acceptance criteria — pass/fail per item
- Advisory, not terminal, in subagent mode; on-disk stays `claimed`; clears on heartbeat — **PASS** (mutation-verified pin).
- Generous hard cap reclaims a hung slot (default 720) — **PASS**.
- Engine emits `STARTING` only for subagent dispatch (best-effort) — **PASS** (shell does NOT emit; emit-failure doesn't crash).
- Display shows `NO-HEARTBEAT` advisory + footer — **PASS**.
- Shell-mode parity preserved (shell no-hb-past-grace still terminal) — **PASS**.
- FR-72/US-18/UC-14 added, no number reuse (FR-61=prompt-from-file, US-17=TUI untouched) — **PASS**.
- 10 reference tests ported to the new `jobs`/`mode` format, mutation-verified — **PASS** (+6 for the extended paths).

## Council (required) — 3-panel self-Council: UNANIMOUS SHIP
`reviews/005_self_council/SYNTHESIS.md`.
- **A (correctness/spec):** SHIP (round 2) — after fixing 4 round-1 findings (the fork was single-prompt only; now also covers multistep `agent` steps + reasoning-gate judges + STARTING emits + a cap>grace `--check`). Judge FR-63 fail-closed preserved (only at the cap, not grace).
- **B (regression-safety):** SHIP — shell parity intact, no false-`done`, advisory display composes with reconcile/tokens, checker still catches real double-dispatch, re-aimed tests not weakened.
- **C (test sufficiency/honesty):** SHIP — all pins bite (load-bearing pin mutation-verified), docs honest, no number reuse, schema knob in both copies.
- **Process:** committed BEFORE the Council (the instr-004 lesson) so a panelist's `git checkout` can't revert uncommitted work.

## Tests
Baseline 447 (`main`) → **463 passed**, run **×3** identical, `python3 -m pytest tests/ -q`, Python 3.14.6. Two mutation-verified PINs: neuter the single-prompt subagent fork OR the multistep step fork → a live no-heartbeat subagent goes `auth_or_launch_failed` → the advisory test FAILS (bites); restored → green. stdlib-only engine preserved (NFR-3). `__pycache__` purged before each post-restore re-verify.

## §9 rows flipped
Added FR-72 / US-18 / UC-14 as a **VERIFIED** §9 row (re-derivation onto the one-format engine; cites `test_subagent_liveness.py`, 16 tests, 2 mutation PINs; FR-40 lineage). No existing rows changed; FR-61/US-17 untouched.

## Notable observations
- **The 4 re-aimed pre-existing tests are a legitimate consequence of FR-72**, not weakening: launch-fail on grace is now shell-dispatch only (the engine's authority domain), so those tests build `mode: shell` jobs; the idempotency test additionally needed shell to avoid the new Layer-B `STARTING`'s legitimate `claimed→running` advance.
- **Scope generalization:** the round-1 implementation matched the single-prompt reference (which predated multistep/gates); the Council correctly pushed it to ALL subagent dispatch paths the merged engine now has. The instruction's concrete-changes #1 explicitly named `_dispatch_step`, confirming the multistep path was in scope.
- **shell mode has no `prompt`** in the strict schema; the test `_shell_entry` carries one as harmless test data (init_run reads `command` for shell), used only to exercise the dispatch machinery.

## Next action expected from orchestrator
Operator review + merge `fr72-subagent-liveness` to `main`, then delete that
branch AND the stale `fr-61-subagent-liveness` reference (per the instruction).
No follow-ups filed beyond that — the feature now covers every subagent dispatch
path the engine owns.
</content>
