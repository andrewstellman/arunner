# Panelist A — fidelity (instr 044)

Charter: each test mirrors its UC at the right rung per `docs/ACCEPTANCE_TESTS.md`;
UC-8 truly runs both rungs; UC-11 confirms the detector FIRES on violations (not just
the happy path); UC-9/10 cover the real in-agent legs, not engine slices.

1. **UC-8 is genuinely two-rung.** `uc8_demo_subagent.json` — all three entries
   `dispatch_mode: subagent`; `uc8_demo_floor.json` — all three `dispatch_mode: shell`
   invoking `{HARNESS_BIN}/demo_worker.py` (no `{STUB}`). Both pass `--check` (exit 0).
   Both grade the SAME `uc8_expected.json`. `test_rung_specific_divergence_is_caught`
   is real: a `(completed,failed,completed)` run produces `runs[run-02].state` +
   `counts[completed]` failures, so the shared expected genuinely rejects a divergence.

2. **UC-11 proves the detector FIRES.** `test_detector_fires_on_the_three_violations`
   drives all three reused `continuation_*` fixtures via `RUNNER.run_scenario`, grades
   each against its own expected (the specific class must be in `violations`), AND
   asserts that claiming `{"violations": []}` FAILS with "continuation violations".
   `_detect_violations` cross-checks each yield's `cited_verdict` vs the engine's
   ground-truth recorded verdict. Not a rubber stamp.

3. **UC-9/UC-10 hit the load-bearing legs.** UC-9 exercises the real
   `incontext.select_next_instruction` (001 → write output → resume at 002, not
   restart; drains to None; STOP forces None mid-queue) + the FR-49 note + a graded
   background run. UC-10 calls the real `jobs.expand_jobs` graded byte-equal to the
   frozen canonical, plus `session_bundle`/`bundle_drifted` + a `--check` clean.

4. **UC-12** drives the real `heartbeat.py wrap` adapter with the command + regex from
   the committed plan; asserts an IN_PROGRESS label shows "step N", never "noise:
   chatter".

Full module 13 passed. The agent-reported scoping (live two-rung drive, fresh-context
rehydrate, NL comprehension recorded in outputs/044) is correctly disclosed and matches
the runbook's disk-gradeable-vs-agent-reported split.

VERDICT: SHIP
