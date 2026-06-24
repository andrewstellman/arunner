# Instruction 005 — re-derive subagent-mode liveness on the unified engine (FR-72)

## What this is
Re-derive the subagent-mode liveness feature (originally built as "FR-61" on the now-stale `fr-61-subagent-liveness` branch / instr 049) **fresh on the unified `main`**, against the post-format-collapse engine. We are NOT merging `fr-61-subagent-liveness` — it was built on the pre-FR-61..65 base and collides with the rewritten engine at 8 sites (and its `FR-61`/`US-17` numbers now clash with shipped features). Re-deriving small on `main` is the single-trunk convention (see `DEVELOPMENT_CONTEXT.md` → Development process). The old branch is the **reference spec only**.

**Renumbering (the old branch reused taken numbers):** this ships as **FR-72**, **US-18**, **UC-14**. (`FR-61` is prompt-from-file; `US-17` is the TUI, both already on `main`. `UC-14` is free.)

## Reference (read first — this is the spec, not code to cherry-pick)
- `git show fr-61-subagent-liveness:docs/REQUIREMENTS.md` — the FR-61 liveness requirement (the three layers + alternative paths + postconditions) and its UC. Re-read it as FR-72/US-18/UC-14.
- `git show fr-61-subagent-liveness:tests/test_subagent_liveness.py` — the 10 tests to port (names below).
- `git show fr-61-subagent-liveness:arunner/engine/tick.py` — the reference implementation (`DEFAULT_SUBAGENT_HARD_CAP_MINUTES=720`, `_emit_subagent_starting`, the `_advance` subagent fork, `launch_advisory`/`_SUBAGENT_ADVISORY_DISPLAY`). **Adapt these to `main`'s current `_advance`/dispatch/`_format_table`; do not paste the old-base versions.**
- Also read on `main`: `docs/REQUIREMENTS.md` (current FR/US/UC numbering + §9), `arunner/engine/tick.py` (current `_advance`, the dispatch path, `_format_table`), `DEVELOPMENT_CONTEXT.md`.

## Branch / base (single-trunk convention)
Create a **short-lived** branch off `main` (e.g. `git worktree add ~/Documents/arunner-fr72 -b fr72-subagent-liveness main`). Implement there, self-Council to SHIP, commit. **Worker does NOT push or merge** — the operator reviews, merges to `main`, and deletes the branch + the `fr-61-subagent-liveness` reference once landed.

## The feature (FR-72 — three layers; spec from the reference, retargeted to the new engine)
Never false-fail a subagent the engine can't observe (the FR-40 analogue for subagent dispatch). On `main`, a run's runtime record still carries `dispatch_mode` ∈ {subagent, shell} (the `mode: agent` plan field dispatches as `subagent`); key the behavior on `dispatch_mode == "subagent"`.

1. **Advisory, not terminal, in subagent mode.** In `_advance`, the `claimed + no-heartbeat-past-`launch_grace` ⇒ auth_or_launch_failed` transition applies **only to shell/Popen workers**. For `dispatch_mode == "subagent"`, a missing heartbeat past grace sets a **non-terminal `NO-HEARTBEAT` display advisory** (`launch_advisory`), the on-disk lifecycle stays `claimed` (slot held), and the run reconciles to `completed`/`failed` when its terminal arrives — never `auth_or_launch_failed`. Clear the advisory when a heartbeat arrives.
2. **Generous hard cap reclaims a hung slot.** Add `subagent_hard_cap_minutes` (plan field, ≫ `launch_grace_minutes`, **default 720** = `DEFAULT_SUBAGENT_HARD_CAP_MINUTES`). A subagent with **no** heartbeat past the cap is reclaimed terminal (`auth_or_launch_failed`) so a hang can't pin a slot forever. Thread it into `_advance` (param or read from `plan`, consistent with how `main`'s `_advance` already takes `plan`).
3. **Engine emits `STARTING` on the subagent's behalf (Layer B).** The subagent-dispatch path writes a `STARTING` heartbeat when it hands the entry to the orchestrator, so `claimed→running` advances next tick regardless of the worker's own beats. Best-effort: a heartbeat-write failure must NOT crash dispatch. (Layer C is doc-only: TOOLKIT.md notes a subagent prompt SHOULD emit `STARTING` first + a terminal last — add that note.)

**Display:** the status table shows the `NO-HEARTBEAT` advisory for an advisory subagent (compose with `main`'s existing reconcile/live-marker/tokens render in `_format_table` — the advisory overlays the displayed state when `dispatch_mode=="subagent"` and `launch_advisory` is set; add an `any_advisory` footer note alongside the existing `any_live`/`any_launch_fail`).

## Concrete changes (confirm exact lines on current `main` first)
1. `arunner/engine/tick.py` — `DEFAULT_SUBAGENT_HARD_CAP_MINUTES = 720`; the `_advance` subagent-vs-shell fork (advisory set/clear + hard-cap reclaim), reading the cap from `plan`; `_emit_subagent_starting(...)` + a call to it on the **subagent** dispatch path (the new `_dispatch`/`_dispatch_step`); the `_format_table` advisory overlay + `any_advisory` footer.
2. `schemas/plan.schema.json` **and** `plugins/arunner/skills/arunner/schemas/plan.schema.json` — add optional `subagent_hard_cap_minutes` (integer, minimum > launch grace; documented default 720). Keep the two copies identical.
3. `docs/REQUIREMENTS.md` — add **FR-72** (the three layers, retargeted), **US-18**, **UC-14**, and a §9 validation row; note the FR-40 lineage. Do NOT reuse FR-61/US-17.
4. `TOOLKIT.md` — the Layer-C subagent-prompt convention note (first beat `STARTING`, last beat terminal).
5. `tests/test_subagent_liveness.py` — port the 10 reference tests to the **new plan format** (`jobs`/`id`/`repo`/`mode`), mutation-verified.

## Tests (red→green, mutation-verified; new `jobs`/`mode` format)
Port these (reference names): `test_no_heartbeat_past_grace_is_advisory_not_terminal` (the load-bearing pin — mutation: delete the subagent fork ⇒ a live subagent goes `auth_or_launch_failed` ⇒ bite), `test_advisory_subagent_reconciles_to_completed_on_return`, `test_advisory_clears_when_a_heartbeat_arrives`, **`test_shell_no_heartbeat_past_grace_is_terminal`** (shell parity — shell still fails past grace), `test_no_heartbeat_past_hard_cap_is_reclaimed_terminal`, `test_default_hard_cap_is_generous`, `test_dispatch_emits_starting_heartbeat`, `test_shell_dispatch_does_not_emit_starting`, `test_starting_then_simulated_return_completes_without_self_heartbeat`, `test_starting_emit_failure_does_not_crash_dispatch`. Full suite `python3 -m pytest tests/ -q` green ≥3× (purge `__pycache__` before any post-restore re-verify); report counts + Python version.

## Self-Council — mandatory 3-panel (reviews/005_self_council/, committed)
- **A — correctness/spec:** the three layers match the FR-72 spec on the *new* engine; advisory is non-terminal + slot-held; the cap reclaims; `STARTING` emitted only for subagent dispatch.
- **B — regression-safety:** **shell-mode parity preserved** (shell no-hb-past-grace still terminal); no false-`done`; the advisory display composes with the existing reconcile/tokens render without breaking either; `auth_or_launch_failed` stays reachable exactly where the engine has authority.
- **C — test sufficiency/honesty:** all 10 pins ported + bite (mutation-verified); FR-72/US-18/UC-14 added (no number reuse); §9 row honest.
Iterate to unanimous SHIP before reporting.

## Commit / output
Focused commits on the short-lived `fr72-subagent-liveness` branch; **worker does NOT push/merge** (operator lands it, then deletes both that branch and the `fr-61-subagent-liveness` reference). Output → `outputs/005-fr72-subagent-liveness-rederive.md`: the before/after, per-test evidence + mutation bites, the FR-72/US-18/UC-14 + §9 rows, the 3-panel synthesis, suite counts ≥3× + Python version, `git log --oneline`.
