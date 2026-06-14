# Panelist B — grading soundness (instr 044)

Charter: the checker CLI grades each UC from durable artifacts; the disk-graded vs
agent-reported split is drawn correctly; reused scenarios are wired right; the mutation
pins bite.

1. **Checker grades from durable artifacts.** Drove the UC-8 floor plan via the real
   ticker and graded with the real checker CLI → `CHECK PASSED ... exit=0`. A real run
   leaves `harness_status.json`, `results/result-NNNNN.json`, per-run
   `heartbeat.ndjson`, `journal.ndjson`, and NO `_check_meta.json` — exactly the set
   `_build_run_dir` synthesizes; `C.check` is the real grader.

2. **UC-11 reuse is real discrimination.** `run_scenario` drives the real engine and
   writes `_check_meta.json` (tick_trace + host_stopped_after_tick + cited yields); the
   detector cross-checks cited-vs-actual against recorded ground truth. The test asserts
   BOTH directions: clean against the fixture's own expected AND that
   `{"continuation":{"violations":[]}}` FAILS.

3. **Mutation pin bites.** Mutated `jobs.py` `_expand_job` `"subagent"`→`"shell"`;
   `Uc10::test_assembled_plan_matches_frozen_canonical` FAILED
   (`'dispatch_mode': 'shell' != 'subagent'`). Restored byte-identical; re-run PASSED;
   tree left clean.

4. **UC-10 frozen canonical is genuine.** `uc10_expected_plan.json` is a committed file
   read via `_plan()`, compared against an independent `expand_jobs(shorthand)` — not
   regenerated at test time. Canonical = pool 2, 3 subagent entries.

5. **UC-12 is a real adapter run.** Drives the real `heartbeat.py wrap` subprocess with
   the command + regex from the committed plan; asserts a `step` label shows while
   `noise: chatter` never does.

Full module 13 passed; `test_checker_independence` green (stdlib-only — the harness
cannot grade its own homework). Final `git status --short` empty; tree left as found.

VERDICT: SHIP
