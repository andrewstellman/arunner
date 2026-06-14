# Traceability/Coverage Council — Panelist A (COMPLETENESS)

**Charter:** adversarial completeness. For each US-1..12 and UC-1..12, does a *built acceptance test* (plan + runbook entry + a gradeable leg or an honest agent-reported leg) actually mirror it? Flag any UC with no plan/no runbook entry, any US not mapped to a test, any "covered" claim resting on the pytest necessary-condition floor rather than an acceptance test, and confirm UC-6/UC-7 are genuinely addressed.

## VERDICT: **GAPS-FOUND**

The acceptance layer is real and well-built for UC-8..12 (disk-graded by `test_acceptance_uc89101112.py`, 26 acceptance tests green: `pytest -k acceptance` → 26 passed, 3 subtests). But the project **cannot yet truthfully claim "every US/UC is mirrored by a *built* acceptance test."** Three structural gaps:

1. **UC-6 and UC-7 have no plan of their own and no driving test.** They were *collapsed into* `uc5_floor.json` (git `ada0866`: "UC-5/6/7 floor plan"). The distinguishing semantics of each — UC-6's "one tick per scheduler *fire*" and UC-7's "repeated manual `--once` until done" — are never exercised as acceptance legs. The only thing standing behind them is `test_ticker.py`, which is the **necessary-condition floor**, not an acceptance test. By this matrix's own definition (TRACEABILITY.md lines 7-8: "Green floor ≠ passing acceptance test"), that is a covered-by-the-floor gap.

2. **UC-1..5 acceptance legs are not built as driving tests.** Their plans + expecteds exist and `--check` clean, but **no test module drives them** the way `test_acceptance_uc89101112.py` drives UC-8..12. The only automated assertion touching them is `test_all_acceptance_plans_check_clean`, which validates that the *plan is well-formed* — not that an acceptance run reaches the expected state. The genuine gradeable mechanics (durable grading, `no_double_dispatch`, `stop_readonly` snapshot) are proven in `test_acceptance_checker.py` against **synthetic `_build_run_dir` fixtures**, not against these UC-1..5 plans driven to `done`. The live in-agent drive is agent-reported (legitimate per the runbook) — but for UC-1..5 *neither* the disk-graded leg *nor* a recorded agent-run exists yet.

3. **The matrix itself says so.** TRACEABILITY.md marks **every row "TO BUILD"** except UC-8 "PARTIAL." The traceability gate (TRACEABILITY.md line 47) says coverage "is claimed only after a council review concludes every US/UC is mirrored by an acceptance test." On the present artifacts that conclusion is **not** supportable for UC-1..7.

The honest status is: **floor green (257 tests); acceptance layer built and disk-graded for UC-8..12; UC-1..7 have plans/expecteds but not built driving tests; UC-6/UC-7 have no plan at all.**

## Coverage table — UC

| UC | Plan | Runbook entry | Built gradeable/agent-reported leg | Status |
|----|------|---------------|-------------------------------------|--------|
| UC-1 Multi-job native | `uc1_multijob.json` (+`uc1_expected`) | yes (ACCEPTANCE_TESTS §UC-1) | **No driving test.** Plan `--check`s clean; durable-grading *mechanics* proven in `test_acceptance_checker.py` on synthetic fixtures, not on this plan; live drive agent-reported but not yet recorded. | **PARTIAL** |
| UC-2 Monitor | `uc2_monitor.json` (+`uc2_expected`) | yes | **No driving test.** `no_double_dispatch` durable grade proven on synthetic fixture (`NoDoubleDispatch`); the "tick-now idempotent" lived leg is agent-self-reported, not built/recorded. | **PARTIAL** |
| UC-3 Halt (STOP) | `uc3_halt.json` (+`uc3_expected`) | yes | **No driving test.** `stop_readonly` snapshot mechanic proven on synthetic fixture (`StopReadonlySnapshot`), not on this plan driven live. | **PARTIAL** |
| UC-4 Resume | `uc4_resume.json` (+`uc4_expected`) | yes | **No driving test.** Floor: `continuation_crash_then_resume`, `resume_continues` scenarios (necessary-condition floor). `no_double_dispatch` durable grade on synthetic fixture. Live re-bootstrap + sleep/hibernate legs agent-reported, not recorded. | **PARTIAL** |
| UC-5 Locked-down floor | `uc5_floor.json` (+`uc5_expected`) | yes | **No driving test.** Plan `--check`s clean; floor is `test_ticker.py` + wrap/tail scenarios. No recorded ticker-to-`done` acceptance run; per-OS (esp. **Windows**) run-context not recorded (NFR-12 / §9 PENDING). | **PARTIAL** |
| UC-6 Scheduled (cron) | **NONE** — folded into `uc5_floor.json` (git `ada0866`) | listed in ACCEPTANCE_TESTS §UC-6 | **No plan, no test.** Scheduler-fires-`--once`, one-tick-per-fire semantics never exercised as an acceptance leg. Rests entirely on the ticker floor. | **MISSING** |
| UC-7 Manual-tick floor | **NONE** — folded into `uc5_floor.json` | listed in ACCEPTANCE_TESTS §UC-7 | **No plan, no test.** Repeated-`--once`-by-hand-until-`done` never exercised as an acceptance leg. Rests entirely on the ticker floor. | **MISSING** |
| UC-8 Demo (2-rung) | `uc8_demo_subagent.json`, `uc8_demo_floor.json` (+`uc8_expected`) | yes | **Built.** `Uc8TwoRung`: both plans `--check`; shared expected accepts a clean run and **rejects a divergence**. Live 2-rung drive recorded in outputs/044 (agent-reported). | **COVERED** |
| UC-9 In-context | `uc9_background.json`, `uc9_instructions/` (+`uc9_expected`) | yes | **Built.** `Uc9InContextQueue`: FR-47 queue **resumes across a fresh context**, STOP halts mid-queue, FR-49 note renders, background grades `done`. "Truly rehydrated" judgement agent-reported (honest). | **COVERED** |
| UC-10 Conversational build | `uc10_build.jobs.json`, `uc10_expected_plan.json` | yes | **Built.** `Uc10ConversationalBuild`: assembled plan == frozen canonical (PIN), pool2/3-subagent shape, saved bundle re-runs clean. NL comprehension agent-reported (honest). | **COVERED** |
| UC-11 Autonomy integrity | `uc11_longrun.json` (+`uc11_expected`) | yes | **Built.** `Uc11AutonomyIntegrity`: long run holds the contract (no CONTINUE-state yield); **detector FIRES** on all three violation fixtures (PIN). Live audit = NFR-12 measurement, not a gate (honestly stated). | **COVERED** |
| UC-12 Activity patterns | `uc12_activity.json` (+`uc12_expected`) | yes | **Built.** `Uc12ActivityPatterns`: drives the **real wrap adapter subprocess**, asserts ACTIVITY shows the relevant line, never the noise. | **COVERED** |

## Coverage table — US

| US | Maps to | Built acceptance test? | Status |
|----|---------|------------------------|--------|
| US-1 overnight multi-repo | UC-1 | inherits UC-1 | **PARTIAL** (UC-1 not built) |
| US-2 status table | UC-2 | inherits UC-2 | **PARTIAL** |
| US-3 STOP file | UC-3 | inherits UC-3 | **PARTIAL** |
| US-4 resume one command | UC-4 | inherits UC-4 | **PARTIAL** |
| US-5 locked-down Windows | UC-5 | inherits UC-5; Windows run-context unrecorded | **PARTIAL** |
| US-6 Codex/Copilot/Cursor dispatch | UC-5 / adapters | floor only (no per-host acceptance run; §9 V-14 is workers-as-detached, not acceptance-driven) | **PARTIAL** |
| US-7 small/cheap model orchestration | UC-1 on a small model | **No acceptance test.** §9 Haiku evidence is a historical spike run, not a UC-1 acceptance leg; not mirrored. | **MISSING/PARTIAL** |
| US-8 pip + paste demo | UC-8 | inherits UC-8 (built); live two-rung recorded | **COVERED** |
| US-9 complete disk record | "every run's disk record" | **No dedicated test.** Asserted as a property of every run, never mirrored by its own acceptance leg; relies on auditability being a side effect. | **PARTIAL** |
| US-10 honest README claims | §9 / `test_positioning_honesty` | `test_positioning_honesty.py` guards framing — but that is a **floor unit test**, not an agent-run acceptance test of the honesty surface. | **PARTIAL (floor-only)** |
| US-11 unattended resists stop-pressure | UC-11 | inherits UC-11 (built) | **COVERED** |
| US-12 activity patterns | UC-12 | inherits UC-12 (built) | **COVERED** |

## Numbered gaps + fixes

1. **UC-6 has no plan and no acceptance test (MISSING).** It is silently folded into `uc5_floor.json`. *Fix:* add `uc6_scheduled.json` + a runbook-driven leg that installs the printed schedule entry (or simulates one `--once` fire per scheduler tick) and asserts exactly one tick advances per fire to `done`, graded by `checker.py`. If UC-6 is *intentionally* equated to UC-5 + UC-7, say so explicitly in TRACEABILITY.md and ACCEPTANCE_TESTS.md ("UC-6/7 share the UC-5 ticker floor; no distinct leg") rather than listing them as separate runbook entries with no backing artifact.

2. **UC-7 has no plan and no acceptance test (MISSING).** Same root cause. *Fix:* either add `uc7_manual.json` + a leg that runs `ticker.py --once` repeatedly until `done` (proving the cadence-4 manual loop, not just that `--once` works once in the floor), or document the deliberate reuse as in gap 1.

3. **UC-1..UC-5 acceptance legs are not built as driving tests (PARTIAL ×5).** The gradeable *mechanics* are proven against synthetic `_build_run_dir` fixtures in `test_acceptance_checker.py`, but no test drives `uc1..uc5` plans to their expecteds. *Fix:* extend the acceptance module (mirror `test_acceptance_uc89101112.py`) to drive the disk-gradeable UC-1..5 plans — at minimum the ticker-drivable shell legs (UC-5, and the ticker leg of UC-4) — through `runner.py`/`ticker.py --once` and grade against `uc{1..5}_expected.json`. For the in-agent-only legs (UC-1/2/3 rung-1 subagent), record a real Claude-Code acceptance run per the runbook so the row flips from agent-reported-pending to agent-reported-recorded.

4. **UC-5 / US-5 / US-6 Windows + per-host run-contexts unrecorded (PARTIAL).** §9 keeps the cadence-2/3/4 + Windows floor **PENDING**; no recorded Windows ticker-to-`done` run exists. A macOS pass does not clear the Windows row (NFR-12). *Fix:* this is a recorded-matrix-run requirement, not a code gap — flag it as the blocking item for any "locked-down floor verified" claim, and keep US-5/US-6 PARTIAL until a Windows run is recorded.

5. **US-7 (small-model orchestration) is not mirrored by an acceptance test (MISSING/PARTIAL).** The matrix maps it to "UC-1 on a small model (recorded)," but no UC-1 acceptance test is built and the only small-model evidence is the historical Haiku spike in §9. *Fix:* once gap 3 lands a UC-1 acceptance leg, add a recorded small-model run of it, or downgrade US-7 to "evidence-only, not acceptance-mirrored" in TRACEABILITY.md.

6. **US-9, US-10 rest on the necessary-condition floor, not an acceptance test (PARTIAL / floor-only).** US-9 (complete disk record) is asserted as a universal property with no dedicated leg; US-10 (honest README) is guarded only by `test_positioning_honesty.py`, a unit test. Per the matrix's own rule ("a 'covered' claim that rests on the floor is not an acceptance test"), neither is mirrored. *Fix:* either add a thin acceptance leg (US-9: assert a completed run-dir is self-sufficient — `summary_present` + `results_for_terminal` + heartbeat completeness, gradeable via `checker.py`; US-10: an agent-reported leg that reads the README support table and confirms VERIFIED/DESIGNED honesty) or explicitly mark them "covered by floor unit test, by design — not an agent-run acceptance test" in TRACEABILITY.md.

## UC-6 / UC-7 confirmation (charter-required)

**Confirmed: not genuinely addressed as acceptance tests — silently folded into the UC-5 ticker floor.** Evidence: (a) no `uc6_*`/`uc7_*` files exist anywhere under `tests/`; (b) git `ada0866` titles the single plan "UC-5/6/7 floor plan"; (c) UC-6/UC-7 appear in `tests/*.py` only inside a `test_ticker.py` docstring ("FR-25, FR-29 / UC-5,6,7") — i.e. the floor, not an acceptance leg; (d) ACCEPTANCE_TESTS.md still lists §UC-6 and §UC-7 as distinct runbook entries, so the runbook over-claims relative to the built artifacts. Their distinguishing behaviors (UC-6: one-tick-per-scheduler-fire; UC-7: repeated manual `--once`) are not exercised anywhere. This is the cleanest "covered claim resting on the floor" instance in the suite.

## What IS solid (so the gaps read in proportion)

- UC-8..12 are genuinely built and disk-graded, with load-bearing mutation pins (UC-10 frozen-canonical fidelity; UC-11 detector-fires-on-three-violations; UC-12 real-subprocess relevance-over-noise).
- The checker is independent stdlib-only (`test_checker_independence.py` enforces it), grades from durable artifacts a real run leaves, and `test_acceptance_checker.py` proves the durable-grading, `no_double_dispatch`, and `stop_readonly` mechanics genuinely *fail* on wrong state (real mutation pins, not rubber stamps).
- All 21 committed acceptance plans `--check` clean (`test_all_acceptance_plans_check_clean`), which would have caught — and per git `696ffe5` did catch — the `uc5_floor` `{STUB}` placeholder defect.
- `pytest -k acceptance` → **26 passed, 257 floor tests deselected**, confirming the built acceptance legs are green.

**Bottom line:** ship the UC-8..12 acceptance layer as built and green, but do **not** stamp "every US/UC mirrored by an acceptance test" until: UC-6/UC-7 are either given real legs or explicitly documented as floor-reuse; UC-1..5 get driving tests or recorded agent runs; and US-7/US-9/US-10 are either mirrored or honestly re-labeled as floor/evidence-only. The matrix's own "TO BUILD" markings already concede this — the gate cannot conclude COMPLETE over them.
