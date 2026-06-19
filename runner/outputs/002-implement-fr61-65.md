# Output for 002-implement-fr61-65.md

**Status:** completed

Implemented FR-61–65 in the tick engine (the multi-step / prompt-from-file / gated-pipeline / token-reporting substrate) in worktree `~/Documents/arunner-fr61-65-impl`, branch `fr-61-65-impl` (off `fr-61-65-spec`). **Local only — not pushed, not merged.**

## Per-FR implementation summary + checkpoint SHAs
| FR | What landed | Checkpoint |
|----|-------------|-----------|
| **FR-61** prompt-from-file + `{var}` | `worker_prompt_file` resolved relative to the plan dir, snapshotted to `run-NN/prompt.snapshot.md` at `--init` (source mutation after init never changes the run); designated-key `{var}` pass (literal `str.replace`) BEFORE reserved placeholders, no stray-brace scan (literal JSON survives); plan/entry/step `vars` merge; `--check` `oneOf` (exactly-one-of worker_prompt/worker_prompt_file/steps/adapter) + reserved-key/value vars guards | `1557c6b` |
| **FR-62** multi-step entries | `steps:[...]` run sequentially in ONE pool slot (`_holds_slot`); each step a full FR-18 sub-run at `run-NN/steps/step-MM/` (heartbeat/manifest/result, `step_index`/`step_count`); dispatch-one-step-per-tick (`_dispatch_step`), advance on clean terminal (`_advance_multistep`); resume reaps-not-re-runs; failed step terminals the entry; table shows `sN/M`; SUMMARY per-step | `ff30411` |
| **FR-63/64** gates + outcomes | shell gate = exit-code→outcome (exit-code only, `stdout=DEVNULL`), `gate.json` persisted + read-on-resume; closed outcomes continue/halt(→FR-55 `failed`)/skip-to-next(synth `SKIPPED`)/behavior-flag:<name>(→next-step `{var}`)/internal_error; out-of-set coerced to internal_error; reasoning gate dispatched as a DISTINCT judge sub-run reading structured `data.verdict`, fail-closed, `--check`-fenced (opt-in, not measurement, distinct judge, no same-context) | `3748e59` |
| **FR-65** token reporting | engine reads EXACTLY `data.usage` into top-level `input_tokens`/`output_tokens` at reap; additive step→entry→run roll-up; TOKENS column (table + monitor) + SUMMARY; honest degradation (`-`/`partial (N of M…)`/skipped-with-warning); never control-flow | `43f8bb9` |
| §9 flips | all five rows PENDING→VERIFIED + v1.4 notes | `d1982b3` |
| Council | 3-panel unanimous SHIP + test-evidence fix | `e6aa7d3` |

`git -C ~/Documents/arunner-fr61-65-impl log --oneline -8`:
```
e6aa7d3 FR-61..65 3-panel council: unanimous SHIP + test-evidence fix (instr 002)
d1982b3 docs: flip FR-61..65 §9 rows to VERIFIED (instr 002)
43f8bb9 FR-65: per-run and per-sub-run token reporting (input + output) (instr 002)
3748e59 FR-63 + FR-64: continuation gates + outcome vocabulary (instr 002)
ff30411 FR-62: multi-step entries (ordered sub-runs) (instr 002)
1557c6b FR-61: prompt-from-file + light {var} templating (instr 002)
aaecd2c FR-61..65 spec: multi-step / gates / prompt-from-file / token reporting (instr 001)
cf67781 FR-60 3-panel council: unanimous SHIP (instr 048)
```

## §9 rows flipped to VERIFIED
FR-61, FR-62, FR-63, FR-64, FR-65 — each with its test reference (`test_prompt_from_file.py` / `test_multistep.py` / `test_gates.py` / `test_tokens.py`). v1.4 status-line + footer updated PENDING→VERIFIED.

## Tests
Baseline (off `fr-61-65-spec`): **334 passed**, Python **3.14.5**. Final: **378 passed** (+44: 13 FR-61, 11 FR-62, 14 FR-63/64, 6 FR-65). Run **3×** — 378 each, deterministic, no flakiness. New engine code is stdlib-only (NFR-3 held; `test_stdlib_only_no_jsonschema` green). The FR-51 independent checker suite (`test_checker_independence.py`, `test_integration_scenarios.py`, `test_acceptance_checker.py`) stays green — the deterministic gate path is graded with no LLM.

Mutation-verified pins (live PASS→break→FAIL→revert, confirmed this session): additive-token-sum, out-of-set→internal_error, behavior-flag-exposed-as-var, no-usage-never-0/0, literal-single-brace-survives, pool1-second-entry-waits, gate-read-on-resume-after-crash (gp.exists), step-reap-idempotent (rp.exists).

## Council (mandatory 3-panel self-Council)
**Unanimous SHIP.** Artifacts: `reviews/002_self_council/` (panelists A/B/C + `synthesis.md`). A — thesis/determinism (disk-truth/NFR-6, FR-51 + measurement fence, tokens reporting-only, shell gate exit-code-only, single-prompt unaffected). B — schema/contract (code matches the edited schemas; resume + gate persistence; closed sets; `halt`→existing FR-55 terminal; heartbeat byte-pin intact; `_holds_slot` one-slot-per-entry). C — test sufficiency (every pin behaviorally asserted; 7 mutations bit across all 5 FRs). C's one accurate finding — two docstring mutation-claims named unexercised defense-in-depth guards — was **resolved before declaring done**: added `test_step_reap_is_idempotent` + `test_gate_read_on_resume_after_crash_does_not_rerun_argv` (crash-window tests that make the guards load-bearing), both mutation-verified to bite; docstrings corrected; no engine change.

## Acceptance criteria — pass/fail
| Item | Result |
|------|--------|
| FR-61 prompt-from-file + `{var}` (snapshot, plan-dir-relative, no stray-brace scan, inline default) | **PASS** |
| FR-62 multi-step (sequential, one slot, per-step disk, dispatch-one-per-tick, resume, `step N of M`) | **PASS** |
| FR-63 shell gate (exit-code-only, gate.json read-on-resume) + reasoning gate fenced | **PASS** |
| FR-64 outcome vocabulary (continue/halt→FR-55/skip-to-next/behavior-flag/internal_error) | **PASS** |
| FR-65 token reporting (data.usage→top-level, roll-up, table/monitor/SUMMARY, honest degradation, never control-flow) | **PASS** |
| §9 rows flipped only when tests prove them | **PASS** (5 rows VERIFIED) |
| FR-51 independent checker still green; stdlib-only | **PASS** |
| Full suite ≥3×, counts + Python version reported | **PASS** (378 ×3, 3.14.5) |
| Checkpoint-commit per FR, local only, no push/merge | **PASS** |

## Notable observations (non-blocking, for the orchestrator)
- **`init_run` does no validation** — a `measurement:true` plan with a reasoning gate that bypassed `--check` would enter judging at runtime. This is the pre-existing "`--check` before `--init`" trust model (NFR-11), not a FR-63 regression; a runtime re-fence would be defense-in-depth.
- **`plan.schema.json` gate object under-documents** `outcomes`/`default`/`judge_prompt`/`judge_prompt_file`/`same_context` (the `--check` enforcer reads them; the schema has no `additionalProperties:false`, so no conflict). A schema annotation would close the doc-drift.
- **FR-64 QPB Phase-3-skip** is proven at the mechanism level (`behavior-flag` → next-step `{var}`); a full 3-step QPB-shaped narrative test is a nice-to-have.
- **Shell/adapter *step* dispatch** and the **monitor TOKENS column** share asserted code paths but aren't separately asserted.

## Next action expected from orchestrator
Review + land the `fr-61-65-impl` branch (operator merges FR branches). The follow-up instruction builds the QPB-native plan (phases as steps, prompts from `phase_prompts/`, gates = `validate_phase_artifacts` shell preconditions) and runs the recall benchmark through arunner instead of `run_playbook`. The engine version bumps to 0.2.0 when that release ships.
