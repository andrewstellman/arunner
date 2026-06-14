# Arunner — Integration Test Plan

*Created 2026-06-14. Companion to `docs/REQUIREMENTS.md` (FR-51 is the integration-suite requirement) and `tests/integration/README.md` (the harness mechanics). This document is the **catalogue of integration tests we run** — what each scenario proves, which FR it covers, and its status — plus the curated **smoke test** and the planned **continuation-contract** test (FR-55).*

## How the suite works (one paragraph)

Every integration test is a folder under `tests/integration/scenarios/<name>/` with a single `scenario.json` = `{description, plan, control?, expected}`. The deterministic ticker (`arunner/engine/ticker.py --once` in a loop, via `tests/integration/runner.py`) drives the run — **never the agent loop**, so it is reproducible and the flaky Class-C path never enters the regression net. The pass/fail verdict comes from `tests/integration/checker.py`, which **imports the standard library only** and reads the disk artifacts (`harness_status.json`, `results/`, heartbeats, claim locks, `_check_meta.json`) — the harness never grades its own homework, and `test_checker_independence.py` enforces that mechanically. Because a scenario *is* an Arunner plan, the suite doubles as the dogfood.

## Smoke test (core-functionality gate)

A small curated subset that validates the core in seconds — the "does the engine still basically work" gate. Defined and runnable at `tests/integration/smoke.py`.

Run: `python3 tests/integration/smoke.py` (exit 0 = all green, 1 = any failure).

| # | Scenario | What it proves | FR |
|---|---|---|---|
| 1 | `autonomous_loop` | autonomous multi-tick loop reaches `done` | FR-1, FR-51 |
| 2 | `stop_readonly` | STOP halts the run and the STOP tick mutates nothing | FR-10, FR-35 |
| 3 | `pool_staggered` | pool limit respected; dispatch staggered (`max_inflight_le`) | FR-7 (pool), FR-51 |
| 4 | `resume_continues` | PAUSE then RESUME: the queued entry dispatches after resume and the run reaches `done` | FR-35, FR-36 |
| 5 | `wrap_adapter_completes` | wrap adapter (shell dispatch) drives to `done` — the cross-agent path | FR-40, FR-54 |

**Last run:** 2026-06-14 — **SMOKE PASSED, 5/5 core scenarios green** (against `main` @ `6dc8016`, full suite 202 passed).

The smoke subset is deliberately tiny and core. New coverage goes in the full catalogue below, not into smoke, unless it is genuinely smoke-level. CANCEL (FR-39) and the live control-file overrides (FR-37/38) are intentionally *excluded* — they are exercised in the full catalogue, not in the fast "does the engine run" gate. Note: FR-13 true crash-resume (`--init` against an existing run-dir) is **not** covered by any current scenario — `resume_continues` is actually a PAUSE/RESUME case (FR-35/36); the planned `crash_then_resume` config (below) closes that gap.

## Full scenario catalogue

All scenarios run under the full suite (`python3 -m pytest tests/`); status reflects the 2026-06-14 run (202 passed).

| Scenario | What it proves | FR | Status |
|---|---|---|---|
| `autonomous_loop` | autonomous multi-tick loop to `done` | FR-1, FR-51 | GREEN |
| `stop_readonly` | STOP halts; STOP tick is read-only (mutates nothing) | FR-10, FR-35 | GREEN |
| `pause_blocks_dispatch` | PAUSE stops new dispatch; run not terminal; RESUME restarts | FR-35, FR-36 | GREEN |
| `poll_now_collapses_cadence` | POLL-NOW forces one immediate tick; inert under PAUSE | FR-38 | GREEN |
| `pool_staggered` | pool limit respected; dispatch staggered | FR-7 (pool) | GREEN |
| `pool_raise_backfill` | POOL raise back-fills next tick; lower drains, never kills | FR-37 | GREEN |
| `cancel_shared_state` | CANCEL frees a stalled run's slot via shared state | FR-39 | GREEN |
| `resume_continues` | PAUSE then RESUME: queued entry dispatches after resume; run reaches `done` | FR-35, FR-36 | GREEN |
| `wrap_adapter_completes` | wrap adapter captures stdout; doneness from exit code | FR-40 | GREEN |
| `tail_adapter_completes` | tail-existing adapter drives an external log to done | FR-41 | GREEN |
| `wrap_output_keyword_no_misreap` | wrap output containing status keywords doesn't cause mis-reaping | FR-40 (edge) | GREEN |
| `continuation_contract` | the FR-55 autonomy-integrity contract (see below) | FR-55 | PENDING |

## Planned: `continuation_contract` (FR-55, UC-11) — the autonomy-integrity test

**What it reproduces.** The 2026-06-14 overnight-stop failure: the orchestrating host stopped an in-flight, non-terminal run while the continue/stop state said "keep going," rationalizing the halt as consideration. The test makes that failure a detectable disk artifact.

**Prerequisite engine work (a worker instruction, not yet built).** FR-55 requires the engine to emit, at the end of every tick, a **continuation verdict** = pure function of run-dir state: `CONTINUE` iff non-terminal ∧ persisted status not paused/stopped/cancelled ∧ no open `blocked:<id>` ∧ progress still possible; else `HALT:<reason>`, `reason ∈ {done, failed, stop, pause, cancel, blocked:<id>, stalled, budget, internal_error}`. The verdict reads *persisted status* (not consumed control-file presence) and carries `next_tick_due` (from the engine's existing `next_tick_minutes`) and a `monitoring_paused` flag (FR-46 in-context burst). Three disk artifacts must exist for the test to read; **pin their shape now so a worker doesn't invent three incompatible ones**:

- **`continuation` field in `harness_status.json`** — `{verdict, reason?, next_tick_due, monitoring_paused}`, computed right after `done` is set in `tick.py`, from the same gating the tick already applies.
- **Per-tick verdict trace** — a one-field extension of the existing per-tick `tick_trace` the integration runner already records in `_check_meta.json`; add the verdict to each entry. No new infrastructure.
- **`journal.ndjson` + blocker record** — the append-only journal carries the per-tick verdict line and the host's `yield` records `{tick, cited_verdict, note}`; a blocker is a `blockers/` entry / `blockers` array `{id, created_at, reason, cleared_at}`.

Until those land the scenario can't be wired; this row stays PENDING.

**Harness extension.** The runner gains a scriptable **stub host** standing in for the LLM orchestrator. Today `runner.py` *is* the host (it ticks to completion); the new knobs make it stop on command and optionally write a yield — categorically different from the existing control-file knobs (which write a file the *engine* reacts to):

- `stop_host_after_tick: N` — the runner **stops driving ticks** after tick N (the host going away).
- `yield_cited: null | "<reason>"` — absent ⇒ no yield written (abandon); present ⇒ a `yield` record citing `<reason>` (legitimate or fabricated).
- `resume_after_stop: true` — after the host stop, the runner re-drives (FR-13 `--init` resume) to prove a crash+resume is *not* abandonment.

The checker (stdlib-only) reads the per-tick verdict trace + the recorded host-stop tick + any yield record, and — crucially — **cross-checks each yield's `cited_verdict` against the engine's actual verdict for that tick**, emitting the violation class.

**Configurations, one base plan** (3 jobs, pool 1, stub workers heartbeat-then-complete, so the run is non-terminal for several ticks, then `done`):

| Config | Host behaviour | Expected from the checker |
|---|---|---|
| `honor` | ticks until the verdict is `HALT:done` | run reached `done`; sole yield cites `HALT:done` matching the engine verdict → **PASS** (detector silent) |
| `abandon` | stops after tick 2 at `CONTINUE`, past `next_tick_due`, **never resumes**, no yield | detector fires **silent abandonment** → test asserts the violation |
| `crash_then_resume` | stops after tick 2 (no yield), then the runner resumes (FR-13) and drives to `done` | detector **stays silent** — terminal non-resumption is false; a recovered crash is not a violation |
| `false-yield` | stops after tick 2; yield cites `"good checkpoint"` (outside the halt set) | detector fires **illegitimate yield** |
| `false-halt-claim` | stops after tick 2; yield cites `"HALT:done"` (in-set, but the engine verdict that tick was `CONTINUE`) | detector fires **false halt claim** (cited ≠ actual verdict) |
| `scheduled_gap_no_false_abandon` | a long gap before the next tick while `now ≤ next_tick_due` (cadence rung), no yield, then ticks to `done` | detector **stays silent** — a scheduled wait is not abandonment |
| `blocked_then_clear` | host records a `blocked:<id>` (verdict ⇒ `HALT:blocked`), yields citing `HALT:blocked`; later the blocker clears and the run resumes to `done` | detector **stays silent** — yield matches the engine verdict; the blocker lifecycle round-trips |

**Verdict-fidelity assertions (deterministic, no host bias needed).** Independently of the yield logic, assert the **verdict value** against known disk state per tick: a STOP file ⇒ `HALT:stop` on exactly that tick; an open blocker ⇒ `HALT:blocked` the next tick; all-terminal ⇒ `HALT:done`; a healthy mid-run tick ⇒ `CONTINUE`. The trace already exists, so this is free and bites the most dangerous engine bug — a verdict that diverges from actual state.

**Red/green meaning.** The detector MUST fire on `abandon`, `false-yield`, and `false-halt-claim`, and stay **silent** on `honor`, `crash_then_resume`, `scheduled_gap_no_false_abandon`, and `blocked_then_clear`. The `abandon` config is the literal reproduction of the incident — work remained, the state said `CONTINUE`, the host stopped and never came back. A green `continuation_contract` means the contract is honored on the happy paths, caught on the three violations, and not false-firing on a recovered crash or a scheduled wait.

**Honest limit (NFR-12).** The stub-host scenario pins the *mechanism* (verdict externalized, the three violation classes detected, no false-fire on crash/scheduled-gap); it does not exercise a real LLM's discretion, and it does not *prevent* a stop — silent abandonment is caught **post-hoc**. To catch a real host, run Arunner driving a real multi-tick job (dogfood) and run the **same** independent checker over the journal afterward: any `CONTINUE`-state stop the real agent commits becomes a recorded violation rather than an invisible judgment. That is measurement, not a deterministic gate — but it converts the bias into an auditable artifact, which is the point. **Residual hole, acknowledged:** the blocker record is host-authored, so a host could fabricate a *genuine-looking* blocker to manufacture a clean yield; the cross-verdict check catches a *mismatched* claim but cannot adjudicate whether a recorded blocker was truly necessary.

## Status / next actions

- The five smoke scenarios and all eleven catalogue scenarios are GREEN as of 2026-06-14 (full suite 202 passed, `main` @ `6dc8016`).
- **Coverage gap:** FR-13 true crash-resume (`--init` against an existing run-dir) is not covered by any current scenario — `resume_continues` is a PAUSE/RESUME case (FR-35/36). The planned `crash_then_resume` config closes it.
- `continuation_contract` is PENDING the FR-55 engine work (emit the per-tick verdict + `next_tick_due`/`monitoring_paused` + blocker records, per the pinned artifact shapes above) + the harness extension (scriptable stub host with `stop_host_after_tick`/`yield_cited`/`resume_after_stop`, the cross-verdict checker). Both are a worker instruction, gated on a self-Council review (the verdict computation touches the engine).
- This section incorporates a 2026-06-14 3-panel sub-agent council on FR-55 + this plan (coherence / testability / honesty); raw reviews under `docs/reviews/FR55_council/`.
