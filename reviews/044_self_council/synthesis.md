# Instruction 044 self-council synthesis — Acceptance tests: UC-8/9/10/11/12

*Mandatory 3-panel. Three fresh-context, role-locked, adversarial reviewers, each
verifying on disk (previewing plans, `--check`ing them, driving the UC-8 floor
plan through the real ticker + grading, running the reused continuation_* violation
fixtures, mutation-biting a pin, confirming the additive diff). Date: 2026-06-14.*

| Panelist | Charter | Verdict |
|----------|---------|---------|
| `panelist_A_fidelity.md` | each test mirrors its UC at the right rung; UC-8 truly two-rung; UC-11 detector FIRES | **SHIP** |
| `panelist_B_grading_soundness.md` | disk-graded honestly; checker grades durable artifacts; pins bite; reuse wired right | **SHIP** |
| `panelist_C_honesty_regression.md` | no overclaim on agent-reported legs; additive; no regression; all plans `--check` | **SHIP** |

## Outcome: unanimous SHIP (round 1)

### Panelist A — fidelity (SHIP)
UC-8 is genuinely two-rung: `uc8_demo_subagent.json` (all entries
`dispatch_mode: subagent`) and `uc8_demo_floor.json` (all `shell` via
`{HARNESS_BIN}/demo_worker.py`, no `{STUB}`) both pass `--check` and grade the SAME
`uc8_expected.json`; `test_rung_specific_divergence_is_caught` proves the shared
expected rejects a `(completed,failed,completed)` divergence (real signal, not an
`or` loophole). UC-11 `test_detector_fires_on_the_three_violations` drives the three
reused `continuation_*` fixtures, asserts the specific class fired AND that claiming
no-violation fails — not a rubber stamp. UC-9 exercises the real
`select_next_instruction` (001 → output lands → resumes at 002, drains to None, STOP
halts mid-queue) + the FR-49 note; UC-10 grades `expand_jobs` byte-equal to the frozen
canonical + the bundle re-run. UC-12 drives the real `heartbeat.py wrap` adapter. The
agent-reported scoping (live two-rung drive / fresh-context rehydrate / NL
comprehension recorded in outputs/044) is correctly disclosed, matching the runbook.

### Panelist B — grading soundness (SHIP)
Independently drove the UC-8 floor plan via the real ticker → `CHECK PASSED exit=0`;
confirmed `_build_run_dir` synthesizes exactly the durable set a real run leaves
(harness_status.json / results / per-run heartbeat.ndjson / journal.ndjson, NO
`_check_meta.json`) and `C.check` is the real grader. UC-11 reuse is genuine
discrimination (asserts both directions). Mutation-bit the UC-10 pin
(`jobs.py` `subagent`→`shell` → the fidelity test FAILED; restored byte-identical →
PASSED; tree left clean). The frozen canonical is a committed file, not regenerated.
UC-12 is a real adapter subprocess driven from the committed plan. `test_checker_independence`
green (stdlib-only — the harness cannot grade its own homework).

### Panelist C — honesty & regression (SHIP)
The module + class docstrings are honest that the agent-reported legs are recorded in
outputs/044, not asserted; no test name implies more than it proves. "Cheap, not free"
preserved. `AcceptancePlansCheck` green; `grep STUB tests/acceptance/plans/` → none.
Full suite **283 passed**; positioning-honesty + checker-independence green. `git diff
--stat 696ffe5 HEAD` = 14 files **all under `tests/`** (12 plans + 1 test file + 2 uc9
fixtures), 0 deletions — NO `arunner/engine/` or `checker.py` mutation (strictly
additive). Expecteds are non-trivial (uc8 requires done+3completed+no_double_dispatch;
uc11 carries the continuation block). A transient 2-test blip the reviewer observed was
a self-inflicted concurrent-pytest artifact (same temp/CWD), did not reproduce in 35+
isolated runs; the UC-10 builders are pure, no xdist — not attributable to the work.

## Net
The remaining acceptance cases land on the 041/042/043 foundation: UC-8 two-rung demo
(subagent rung-1 + shell rung-3 against one expected; divergence catchable), UC-9
in-context queue-resume across a fresh context (FR-47/48) + STOP-halt + FR-49 note,
UC-10 conversational-build plan-fidelity against a frozen canonical + faithful bundle
re-run, UC-11 long-run contract + the detector firing on the three violation fixtures
(mutation-pinned), UC-12 real-adapter relevant-not-noise. The load-bearing legs were
demonstrated live by the worker: UC-8 driven to `done` at BOTH rungs (checker exit 0
against the same expected), UC-11 driven in-agent (4 subagents, journal CONTINUE×4 →
HALT:done, no CONTINUE-state yield, checker exit 0). Suite 270 → 283; both pins bite;
strictly additive. UC-8..12 close the acceptance layer; cross-platform / per-agent runs
remain the operator's (a macOS Claude Code pass does NOT clear the §9 Windows floor row).
