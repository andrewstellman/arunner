# Panelist B — FIDELITY AT THE GATE

**Charter:** Does each BUILT acceptance test mirror its use case at the right rung, or did the build drift into grading the engine slice? (Adversarial review of BUILT artifacts, not the council-reviewed design.)

**Verdict: SHIP-THE-COVERAGE** — with two non-blocking fidelity notes (N-1, N-2) and one watch-item (W-1). Every UC I could grade mirrors its lived case at the correct rung; the two "did it drift into the engine slice" traps the charter named (UC-2, UC-11) are avoided by construction, and I verified the UC-11 detector genuinely FIRES end-to-end (not a rubber stamp).

## What I ran (evidence, not inference)

- `pytest tests/test_acceptance_uc89101112.py -q` → **13 passed, 3 subtests passed**.
- Drove all four continuation scenarios through `tests/integration/runner.py` + graded with the real `checker._detect_violations` / `checker.check`:
  - `continuation_abandon` → detected `['silent_abandonment']`; grades clean vs its own expected; **claiming no-violation FAILS** (detector fired).
  - `continuation_false_yield` → `['illegitimate_yield']`; claim-none FAILS.
  - `continuation_false_halt_claim` → `['false_halt_claim']`; claim-none FAILS.
  - `continuation_honor` → `[]`; claim-none passes (correctly silent).
- Dumped `dispatch_mode` for every acceptance plan and cross-checked the rung matrix.
- Read `incontext.select_next_instruction`, `jobs.expand_jobs`, `checker.check`, and both UC-9 instruction fixtures.

## Right rung? (dispatch_mode vs the in-agent/ticker matrix)

Confirmed by reading the actual `entries[].dispatch_mode` in each plan:

| UC | Required rung | Plan | dispatch_mode | OK? |
|----|---------------|------|---------------|-----|
| 1  | in-agent (subagent) | `uc1_multijob.json` | subagent | ✓ |
| 2  | in-agent | `uc2_monitor.json` | subagent | ✓ |
| 3  | in-agent | `uc3_halt.json` | subagent | ✓ |
| 4  | in-agent | `uc4_resume.json` | subagent | ✓ |
| 5  | ticker (shell) | `uc5_floor.json` | shell | ✓ |
| 8  | BOTH | `uc8_demo_subagent.json` / `uc8_demo_floor.json` | subagent / shell | ✓ (genuinely two plans, one shared expected) |
| 9  | in-agent | `uc9_background.json` | subagent | ✓ |
| 11 | in-agent | `uc11_longrun.json` | subagent | ✓ |
| 12 | ticker (shell adapter) | `uc12_activity.json` | shell, `adapter:"wrap"` | ✓ |

No in-agent case uses shell; no floor case uses subagent. UC-8 is the only BOTH case and it is built as two real plans graded against the **same** `uc8_expected.json`, which is exactly what makes a rung-specific divergence catchable — and `Uc8TwoRung::test_rung_specific_divergence_is_caught` proves the shared expected REJECTS a one-job-failed run. Correct.

UC-6/UC-7 (cadence 2/4, ticker `--once`) carry no dedicated plans, which is right per ACCEPTANCE_TESTS §"Two run paths": they re-drive a shell-dispatch plan via cron / by-hand `--once`. They are the genuinely-PENDING Windows/cron floor matrix (REQUIREMENTS §9), not a fidelity gap in the built artifacts.

## Mirrors the lived case, or the engine slice? (the charter's five traps)

**UC-2 (tick-now idempotency, NOT table serialization) — PASS.** `uc2_expected.json` grades `no_double_dispatch: true`, and the checker (§9, lines 330–349) implements that as "each run's `heartbeat.ndjson` has ≤ 1 STARTING line" — i.e. the *lived* "run another tick now and confirm nothing double-dispatches" affordance from UC-2's basic course, read off the durable disk artifact a real run leaves. It does **not** assert table-string equality; the module docstring and ACCEPTANCE_TESTS §UC-2 both explicitly hand table-vs-status serialization to the floor's `test_cli`. The trap is named and avoided.

**UC-8 (genuinely two rungs vs one expected) — PASS.** Two plans, one expected, divergence-rejection test present (see above). Not one rung pretending to be two.

**UC-9 (fresh-context rehydrate + in-context queue, not just background run-dir) — PASS, and this is the load-bearing one.** `Uc9::test_queue_resumes_across_a_fresh_context` calls `select_next_instruction` (a pure filesystem scan: lowest `NNN-` instruction with no matching output stem on disk), writes the `001` output, then calls it AGAIN and asserts it returns `002` — i.e. a fresh context resumes the *in-context queue* from disk state alone, not from a memory pointer, and not merely the background run-dir (which is graded separately in `test_background_run_grades_done`). I read both committed fixtures: `002-trivial-note.md` literally documents "after the session is killed and rehydrated in a FRESH context … resumes the IN-CONTEXT QUEUE here (task 002)". `test_stop_halts_the_queue_mid_stream` confirms STOP forces selection to None with 001/002 still unprocessed (read-only mid-queue halt). The "busy, not asleep" FR-49 leg renders via `monitoring_pause_note`. This mirrors UC-9's actual basic course, not an engine-queue unit slice.

**UC-10 (assembled plan vs a FROZEN canonical, not a fixed-prompt engine echo) — PASS.** `Uc10::test_assembled_plan_matches_frozen_canonical` (a mutation PIN) expands `uc10_build.jobs.json` via `jobs.expand_jobs` and asserts byte-equality against the committed `uc10_expected_plan.json` (pool 2, three subagents, placeholder header injected). `test_saved_bundle_reruns_faithfully` confirms the bundle carries both shorthand + expanded, reads non-drifted, and the expanded plan is `--check`-clean. The NL-comprehension leg is honestly left to agent-self-report (the shorthand already inlines "(the contents of ABC.md)" — the file-read is the agent's job, not the tool's). This is fidelity to UC-10's "assemble → expand → persist → faithful rerun", graded against a frozen artifact, exactly as the charter demands.

**UC-11 (detector FIRES on the 3 violations, not just happy path) — PASS, verified independently.** `test_detector_fires_on_the_three_violations` (the second mutation PIN) drives all three deliberate-violation fixtures through the real runner and asserts both that each grades clean against its own expected AND that claiming `violations: []` FAILS. I re-ran this outside pytest against `checker._detect_violations` and confirmed each scenario emits its distinct class and that the honor scenario stays silent (table above). The three fixtures are materially different (stop-at-CONTINUE-past-due / yield citing out-of-set "good checkpoint" / yield citing in-set "HALT:done" while engine said CONTINUE), so this is genuinely the three-class detector, not three copies of one. `test_long_run_holds_the_contract` covers the happy multi-tick CONTINUE→HALT:done path with no CONTINUE-state yield. This is the reason FR-55 exists and the build tests it adversarially.

**UC-12 (detector fires on real noisy output, not happy path) — PASS.** `test_wrap_activity_label_is_relevant_not_noise` shells the REAL `heartbeat.py wrap` subprocess over the committed noisy command (`noise: chatter` interleaved with `step N`), with `--activity-regex` taken from the plan, and asserts IN_PROGRESS labels show a `step` line and NEVER `noise: chatter`. Drives the actual adapter, mirrors UC-12's lived "surface the relevant line from a chatty tool" — not a matcher unit slice.

## Disk-graded vs agent-reported — honestly drawn?

Yes. The module docstring and ACCEPTANCE_TESTS §"Disk-gradeable vs. agent-reported" draw the line cleanly and the code honors it:
- **Disk-graded:** UC-8 shared-expected + divergence, UC-9 queue-resume / STOP-halt / background done, UC-10 frozen-canonical + bundle rerun, UC-11 contract-hold + 3-class detector, UC-12 real-adapter relevance.
- **Agent-self-reported (correctly NOT asserted here, deferred to outputs/044):** UC-8's live two-rung drive, UC-9's "did the fresh context *truly* rehydrate", UC-10's NL comprehension.
- The checker is honest about its own limits: meta-only keys (`max_inflight_*`, cadence bounds, `byte_identical_results`, the per-tick continuation trace) are **flagged** as needing the runner meta rather than silently passing when absent (checker lines 182–185, 28–32). That is the right kind of honesty for a live-run grader.

## Fidelity notes (non-blocking)

- **N-1 (UC-11 `verdict_present` is a presence check, not an ordering/coverage check).** `uc11_expected.json` asserts `CONTINUE` and `HALT:done` each appear *somewhere* in the journal verdicts (checker lines 315–318). It does not assert "every non-final tick was CONTINUE and exactly the final was HALT" — a run that emitted one stray `HALT:stalled` mid-stream then recovered could still satisfy presence. The contract-hold property (no CONTINUE-state yield) IS strongly pinned via the violations detector, so the autonomy-integrity claim is safe; this is a "the verdict-sequence shape is under-asserted" nit, not a hole. Consider a follow-up assertion that all non-final verdicts are CONTINUE if you want sequence fidelity, not just presence.
- **N-2 (UC-10 fidelity rides entirely on `expand_jobs` determinism).** The frozen-canonical pin is excellent, but the canonical was authored by the same expander it grades; the only thing keeping them honest is that `uc10_expected_plan.json` is a committed separate artifact a human can eyeball. That is acceptable (it catches expander drift, which is the real risk), but it does not catch "the agent assembled the wrong shorthand" — correctly delegated to agent-self-report. Drawn honestly; noting the boundary.

## Watch-item

- **W-1 (workspace bash flakiness, not a product defect).** My isolated Linux workspace wedged on a long-running command early in the review; I completed all execution via retries and verified results directly. No bearing on the artifacts — flagged only so a re-runner isn't surprised.

**Bottom line:** the BUILT UC-8..12 acceptance tests mirror their lived use cases at the correct rung and grade the right durable disk artifacts; the two named drift-traps (UC-2 idempotency-not-serialization, UC-11 fires-not-rubber-stamps) are avoided and I confirmed the UC-11 detector fires on all three violations and stays silent on the honest run. SHIP-THE-COVERAGE.
