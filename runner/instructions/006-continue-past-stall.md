# Instruction 006 — continue-past-stall (FR-74) + output-activity liveness (FR-73)

## What this is
The gen-007 widenet baseline run **HALTed on stalled workers** — a pool-2 subagent run returned `HALT:stalled` with 43 jobs unstarted. Root cause (verified in `tick.py` on current `main`): a heartbeat-quiet worker is marked `stalled` (engine-derived, `tick.py:1737-1739`), which is **non-terminal** (`_TERMINAL_STATES` excludes it, `:109`) and **non-killable in the MVP** (`:32`), yet still counts as **inflight** (`_INFLIGHT_STATES`, `:110`; recounted inline at `:1464-1465`). So once both pool slots are `stalled`, `pool − inflight == 0`, no queued job can dispatch, and `_halt_reason` returns `"stalled"` → HALT (`:1468-1470`). One hung worker per slot wedges and halts an entire unattended batch.

**Fix:** a `stalled` run goes terminal-after-grace (reclaim its slot → the batch continues) — **but only when its output is ALSO stale**, so a quiet-but-working worker is never abandoned. That output-freshness signal is FR-73's `OUT-AGE`, which is why **FR-74 and FR-73 land together in this one instruction** (per the operator-approved review: shipping a time-only reclaim risks abandoning the very workers it's meant to protect — `source-controller` in gen-007 was heartbeat-silent ~34 min while writing 26 files). Spec: `docs/PLANNED_run_robustness.md` (§4).

## Prerequisite (sequencing — do NOT start before this)
This work builds on **FR-72** and lands on **`main`** (single-trunk, per `SDLC.md`). Before starting, the arunner consolidation must be done: FR-72 (`366a5bd`) merged to `main`, and the stale `fr72`/`fr-61` worktrees + branches pruned. FR-74/FR-73 touch the same `_advance` / `_dispatch` / `_format_table` regions FR-72 did, so they must sit on top of it. Confirm `git branch --contains 366a5bd` shows `main` before starting.

## Renumbering
Ships as **FR-74** (reclaim-and-continue — top priority) + **FR-73** (`OUT-AGE` output-activity liveness). Assign **US/UC at next-free** per `REQUIREMENTS.md` after FR-72's US-18/UC-14 — do **not** reuse numbers (cf. the 005 renumbering note).

## Reference (read first — spec, not code to paste)
- `docs/PLANNED_run_robustness.md` — the consolidated run-robustness design: §1 (gen-007 incident), §4 (FR-74 + FR-73 spec: root cause with line cites, layered fix, the OUT-AGE cross-read), §9 (invariants). (Supersedes the former `docs/PLANNED_FR73_run_observability.md`, now in `docs/archive/`.)
- The **gen-007 run dirs** — `harness_runs/20260622T193505Z/` (the 15-job plan + `defu`/`goshs` manifests + queue) and `harness_runs/20260622T193939Z/journal.ndjson` (the 18-tick `HALT:stalled`) — needed for the pre-build calibration below. Target-repo output mtimes are in `QPB/repos/secbench2_widenet/`.
- On `main` (post-FR-72): `tick.py` (`_advance` `:1660`+, `_halt_reason` `:1448-1471`, `_INFLIGHT_STATES` `:110`, `_TERMINAL_STATES` `:109`, the stall assignment `:1737-1739`, `_format_table` `:2551`+), `STATE_MACHINE.md`, `docs/REQUIREMENTS.md`, `SDLC.md`.

## Branch / base (single-trunk)
Short-lived branch off **`main`**, e.g. `git worktree add ~/Documents/arunner-fr74 -b fr74-continue-past-stall main`. Implement, self-Council to SHIP, commit. **Worker does NOT push/merge** — operator lands it onto `main` + deletes the branch.

## Step 0 — pre-build calibration (concern #2 — do this FIRST; it decides the design)
Before writing code, establish from the gen-007 run-dirs (`harness_runs/20260622T193505Z/` + `harness_runs/20260622T193939Z/journal.ndjson`; target-repo output mtimes in `QPB/repos/secbench2_widenet/`) whether the workers that triggered `HALT:stalled` (`defu`, `goshs`) had **stale output** at HALT time (genuinely hung → reclaim is the right fix) or **fresh output** (alive but heartbeat-quiet → the engine *false-stalled* them, and the load-bearing fix is the OUT-AGE-aware stall guard, not the reclaimer). Record the finding in the output file. It (a) confirms whether reclaim vs. don't-false-stall is the primary fix, and (b) calibrates `stall_reclaim_minutes`. **If `defu`/`goshs` were quiet-but-working, the output-freshness guard is not optional — it is the whole fix**, and a time-only reclaim would have abandoned live workers.

## FR-73 — `OUT-AGE` output-activity signal (build first; FR-74's guard depends on it)
1. **Data layer (shared, pure-stdlib):** compute the age of the most-recent write under a run's output area (default: its `target_repo` working tree, or a per-entry/plan `output_globs`), **newest-mtime only, bounded + cached** (file-count/age cap; never a full recursive walk per render). Lives in the pure-stdlib data layer the monitor/TUI already share (NFR-3: no new dependency).
2. **Display:** an `OUT-AGE` column in `_format_table` (`:2551`+, between `HB-AGE` and the FR-65 `TOKENS` column). One renderer → it appears in the engine table, `arunner monitor`, and `arunner tui` (FR-71: no forked renderer).
3. **Invariant — display-only:** the rendered `OUT-AGE` is **never** read by `_advance` / `_dispatch` / `_terminal_status`. Doneness stays "the declared terminal status." (FR-74's reclaim guard consumes the *data-layer mtime signal* directly — that is a data read, not a read of the rendered column; keep the distinction sharp so the display-only invariant stays literally true.)

## FR-74 — reclaim a stalled slot and continue (engine; consults the OUT-AGE signal)
1. **`stall_reclaim_minutes`** (plan field; default ≫ `stall_threshold_minutes` but ≪ FR-72's 720-min cap — e.g. 2–3× the stall threshold; calibrate from Step 0). A run `stalled` past `stall_reclaim_minutes` **AND whose output is also stale** (OUT-AGE past a freshness window) transitions to terminal **`abandoned`** — drops out of `_INFLIGHT_STATES` → `free_slot` opens → the queue dispatches. **A stalled run whose output is FRESH is NOT reclaimed** (the quiet-but-working guard — the gen-007 false alarm). This is the continue-past-stall guarantee: a genuinely-hung worker costs its own job, not the batch.
2. **`abandoned`, not `failed`** (honest — we gave up waiting; we did not observe a failure; `abandoned` is already terminal). Optional **`stall_retries`** (default 1): a reclaimed stalled job MAY requeue once before abandon — Council picks requeue-vs-abandon as the default.
3. **Reserve `HALT:stalled` for the genuinely-unrecoverable wedge** — the `_halt_reason` stalled branch (`:1468-1470`) only fires when reclamation is disabled, or a stalled-but-output-fresh run cannot be reclaimed. HALT becomes the rare last resort, not the default response to any pool-saturating stall.
4. **Subagent reclaim is an ACCOUNTING free, not a kill (concern #3).** Subagent mode has no kill semantics (`:32`) — reclaiming frees the engine's accounting slot but cannot stop the in-session subagent, which may keep running and later write a terminal line. Handle idempotently: a reclaimed-as-`abandoned` run that **later emits a terminal `completed`/`failed` must NOT resurrect, double-count, or double-dispatch** (its slot may already be reused) — reconcile to one stable terminal. Document that actual concurrency may briefly exceed `pool_size` in subagent mode (acceptable; FR-74 is cleanest in **shell** mode where the process is killable).
5. **Compose with FR-72, don't duplicate:** FR-72 = *launch* liveness (advisory + 720-min cap, keyed on `launch_grace`, never-heartbeated). FR-74 = *mid-run* reclaim (keyed on `stall_threshold` / `stall_reclaim`, heartbeated-then-stale). Lifts the `:32` non-killable-MVP limitation for the stall path specifically.

**Display:** a reclaimed run shows a terminal `STALLED→ABANDONED` row; the footer notes `N stalled-reclaimed`. `HB-AGE 34m / OUT-AGE 40s` reads "alive, just quiet"; `HB-AGE 34m / OUT-AGE 34m` reads "really hung."

## Concrete changes (confirm exact lines on post-FR-72 `main` first)
1. `arunner/engine/tick.py` — the OUT-AGE data-layer fn (bounded newest-mtime scan + per-render cache); the `_format_table` `OUT-AGE` column; the FR-74 reclaim in `_advance` (stalled-past-reclaim **AND** output-stale → `abandoned`; optional requeue-once); the `_halt_reason` stalled branch reserved for the unrecoverable case; the reclaimed-worker-comeback idempotency.
2. `schemas/plan.schema.json` **and** `plugins/arunner/skills/arunner/schemas/plan.schema.json` — add optional `stall_reclaim_minutes` (int, > `stall_threshold_minutes`), `stall_retries` (int, default 1), `output_globs`. Keep both copies identical.
3. `docs/REQUIREMENTS.md` — **FR-74** + **FR-73** (layers + alternative paths + postconditions), US/UC next-free, §9 validation rows; note the FR-40 / FR-72 lineage and the `OUT-AGE` display-only invariant.
4. `STATE_MACHINE.md` — the new `stalled → abandoned` terminal edge (reclaim-after-grace); note `stalled ↔ running` reversibility still holds **below** the reclaim threshold.
5. `TOOLKIT.md` — (optional) the `HB-AGE`/`OUT-AGE` reading note for operators.
6. `tests/` — the pins below.

## Tests (red→green, mutation-verified; `jobs`/`mode` format)
- **`test_pool2_two_stalled_with_queue_drains_not_halt`** — THE gen-007 load-bearing pin: pool-2, both slots stalled past reclaim with output stale, 40+ queued → the queue **drains** (reclaim → dispatch); `_halt_reason` never returns `"stalled"`. Mutation: remove the reclaim ⇒ `HALT:stalled` ⇒ bite.
- **`test_stalled_but_output_fresh_is_NOT_reclaimed`** — the quiet-but-working guard (the false-alarm pin): heartbeat stale past reclaim BUT OUT-AGE fresh → run stays held, NOT abandoned. Mutation: drop the output-freshness guard ⇒ a live worker is abandoned ⇒ bite.
- `test_reclaimed_stall_is_abandoned_and_frees_slot` (terminal + inflight drops + a queued job dispatches).
- `test_reclaimed_worker_late_terminal_does_not_resurrect_or_double_dispatch` (concern #3 idempotency / the comeback race).
- `test_halt_stalled_still_reachable_when_reclaim_disabled` (HALT:stalled preserved for the true wedge).
- `test_stall_retry_once_then_abandon` (if requeue is the default).
- `test_out_age_is_display_only_not_lifecycle` (deleting lifecycle code still bites; deleting `OUT-AGE` changes only the rendered table) + `test_out_age_newest_mtime_correct` + a bounded-scan-cost assertion.
- Shell-mode parity preserved; FR-72 launch path unchanged. Full suite `python3 -m pytest tests/ -q` green **≥3×** (purge `__pycache__` before any post-restore re-verify); report counts + Python version.

## Self-Council — mandatory 3-panel (`reviews/006_self_council/`, committed)
- **A — state-machine/correctness:** `stalled→abandoned` transition correct; slot freed; **no false-abandon of a still-live worker** (the output-fresh guard holds); `stalled↔running` reversibility intact below the reclaim threshold; the reclaimed-comeback race reconciles idempotently.
- **B — regression-safety:** `HALT:stalled` still reachable for the genuine unrecoverable wedge; shell parity; CANCEL still works; no double-dispatch on requeue; FR-72 launch path unchanged; `OUT-AGE` display-only (never a lifecycle input); renderer parity across engine/monitor/TUI; stdlib-only, bounded scan.
- **C — tests/honesty:** the gen-007 drain pin AND the output-fresh-no-reclaim pin both present + mutation-bite; FR-74/FR-73 + US/UC added (no number reuse); §9 honest; the Step-0 gen-007 calibration finding recorded.
Iterate to unanimous SHIP before reporting.

## Commit / output
Focused commits on the short-lived `fr74-continue-past-stall` branch; **worker does NOT push/merge** (operator lands + deletes the branch). Output → `outputs/006-continue-past-stall.md`: the Step-0 gen-007 calibration finding (concern #2), before/after, per-test evidence + mutation bites, the FR-74/FR-73 + US/UC + §9 rows, the `STATE_MACHINE.md` delta, the 3-panel synthesis, suite counts ≥3× + Python version, `git log --oneline`.
