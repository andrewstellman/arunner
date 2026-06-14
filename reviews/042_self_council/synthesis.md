# Instruction 042 self-council synthesis — Acceptance tests: lifecycle (UC-2/3/4) + floor (UC-5/6/7)

*Mandatory 3-panel. Three fresh-context, role-locked, adversarial reviewers, each verifying on disk (previewing plans, re-grading via the CLI, driving the floor plan through the ticker, mutation-biting the no_double_dispatch pin, reproducing the E2 wall-clock-jump guard). Date: 2026-06-14.*

| Panelist | Charter | Verdict |
|----------|---------|---------|
| `panelist_A_fidelity.md` | each test mirrors its UC at the right rung | **SHIP** |
| `panelist_B_grading_soundness.md` | grading from durable artifacts, real + pinned | **SHIP** |
| `panelist_C_honesty_regression.md` | honesty & regression | **SHIP** |

## Outcome: unanimous SHIP (round 1)

### Panelist A — fidelity (SHIP)
UC-2/3/4 are genuine rung-1 subagent plans (every entry `dispatch_mode: subagent` + the trivial heartbeat `worker_prompt`, no `worker_cmd`/`adapter`; all three `--check: OK`). UC-2's expected grades `no_double_dispatch` (the idempotent tick-now affordance), NOT table-vs-status text. UC-4 (pool 1 → entry-2 queued mid-run) covers both resume legs (fresh re-bootstrap + `ticker.py --once`) and the hibernate leg; the E2 wall-clock-jump guard in `tick.py` (`suppress_stall` gated by `_WALLCLOCK_JUMP_FACTOR`, plus terminal-reap-before-stall) prevents a false STALL. UC-5 floor is real shell-dispatch via the ticker (its `--check` on the `{STUB}` placeholder fails standalone exactly like every existing shell scenario — the runner substitutes it — not faked in-agent).

### Panelist B — grading soundness (SHIP)
`no_double_dispatch` is sound and PINNED: section 9 counts STARTING lines per run's heartbeat, fails on >1 (the FR-6 idempotency signal). Mutation bite (`if False and starts > 1:` + pycache purge) made the `# PIN` `test_double_start_fails` fail while single-start still passed; restored byte-identical. The UC-3 snapshot-compare is real (byte-identical passes, a cycle-changed snapshot fails, missing snapshot flagged). The CLI grades from durable artifacts (exit 0 clean; exit 1 after injecting a second STARTING). The UC-5 floor plan drove `ticker.py --once` to done (3 completed, each STARTED ×1) and `checker.py <run-dir> uc5_expected.json` → exit 0. Full suite 269.

### Panelist C — honesty & regression (SHIP)
`uc5_floor.json` is genuinely `dispatch_mode: shell` + `worker_cmd` (ticker-driven, not faked in-agent — a rung-1 agent refuses a shell plan, which IS UC-5's hand-off). `test_positioning_honesty.py` 7 passed with the §9 Windows floor row staying PENDING. Full suite 269 (267 + 2); the `checker.py` diff is strictly additive (the gated section 9 + docstring; sections 1–8 untouched); `test_checker_independence` 2 passed; `test_integration_scenarios` 4 passed. No floor case faked, no disk-vs-reported overclaim, no coverage/platform overclaim, zero regression.

## Net
The lifecycle + floor acceptance tests land on the 041 foundation: a new durable `no_double_dispatch` grade (≤1 STARTING per run's heartbeat — the FR-6 signal, mutation-pinned); UC-2/3/4 subagent stub plans (`--check`-clean); a UC-5/6/7 shell floor plan driven by the ticker (UC-5 foreground / UC-6 per-schedule-fire / UC-7 by-hand share the `ticker.py --once` mechanism). The load-bearing **UC-4 resume** was demonstrated end-to-end by the worker at rung-1: **leg (a)** agent re-bootstrap dispatch-resume (reap the done entry, dispatch the queued one) → `done`, STARTING=1/run; **leg (b)** `ticker.py --once` reap-resume with `ARUNNER_NOW` jumped +999999s (hibernate) → reaped to `done` with no false STALL; both graded by the checker CLI (exit 0). Suite 267 → 269. UC-8/9/10/11/12 are instruction 043.
