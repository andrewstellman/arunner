# Panelist C — Test sufficiency (FR-61..65 implementation, instr 002)

**Charter:** do the tests PROVE the acceptance pins, and do the mutation-pins BITE? (ran pytest + live mutation probes, reverting each.)

**Per-FR pin coverage** — every docs/REQUIREMENTS.md acceptance pin for FR-61..65 has a behavioral test assertion:
- **FR-61** (`test_prompt_from_file.py`, 13): byte-for-byte dispatch, inline regression, plan-dir-relative-from-other-cwd, snapshot-authoritative, `{skill_fallback_guide}` round-trip, literal-single-brace-survives (+ clean `--check`), both/zero-source `--check` error, vars reserved-key + reserved-token-value errors (entry + plan level). Fully covered.
- **FR-62** (`test_multistep.py`, 11): 3-step ordering, pool_size:1 second-entry-waits, step_index/step_count on disk + table, resume-no-rerun + step-03 dispatch, crash-between-reap-and-dispatch, failed-step terminals entry w/ per-step failure, `--check` prompt+steps, SUMMARY per-step, **reap-idempotency**.
- **FR-63** (`test_gates.py`): each shell outcome drives sequencing + recorded; **read-on-resume after crash** (argv not re-run); reasoning rejected without opt-in / in measurement; same-context = error; missing-judge = error; separate-context judge verdict applied + identity recorded; malformed verdict fail-closed.
- **FR-64**: continue/halt(→FR-55 failed)/skip-to-next(synth SKIPPED)/behavior-flag(exposed as next-step `{var}`)/out-of-set→internal_error.
- **FR-65** (`test_tokens.py`, 6): usage→result + table, additive roll-up (150=100+50), no-usage→`-` never 0/0, partial labeled, malformed skipped-with-warning, tokens-never-change-done.

**Mutation probes performed (PASS → break → FAIL → revert; tree clean after each):** 7 distinct biting mutations spanning all five FRs —
1. `_add_tok` overwrite-not-sum → `test_additive_rollup_multistep` BIT.
2. drop out-of-set→internal_error coercion → `test_shell_out_of_set_outcome_is_internal_error` BIT.
3. drop `flags[flag]` set → `test_behavior_flag_exposed_as_next_step_var` BIT.
4. `_tokens_cell` None→0 → `test_no_usage_shows_dash_never_zero` BIT.
5. `_PLACEHOLDER_TOKEN_RE` scan-all-braces → `test_literal_single_brace_json_survives` BIT.
6. `_holds_slot` return False between steps → `test_pool1_second_entry_waits` BIT.
7. **drop `_evaluate_gate` gp.exists() guard → `test_gate_read_on_resume_after_crash_does_not_rerun_argv` BIT** (added this round); **drop `_reap_step` rp.exists() guard → `test_step_reap_is_idempotent` BIT** (added this round).

**FR-51 discipline:** `test_checker_independence.py` + `test_integration_scenarios.py` + `test_acceptance_checker.py` pass; the deterministic gate path is exit-code-only (no stdout), reasoning gates are `--check`-rejected in measurement/FR-51/FR-55 runs and judged in a distinct sub-run. No LLM in the grader.

**Full suite:** `python3 -m pytest -q` → **378 passed**, run 3×, identical, no flakiness.

**Original finding (now RESOLVED):** two docstring mutation-claims (resume-no-rerun's `rp.exists()`; gate read-on-resume's `gp.exists()`) named guards the *original* tests did not exercise (those tests proved the correctness property via the step_index-advance mechanism, but the named guards were unbitten defense-in-depth for the crash window). Resolved by adding `test_step_reap_is_idempotent` + `test_gate_read_on_resume_after_crash_does_not_rerun_argv`, which make those guards load-bearing; both mutations now BITE (verified above), and the docstrings were corrected to match.

**Remaining low-severity notes (non-blocking):** FR-64 QPB Phase-3-skip is proven at the mechanism level (flag → next-step var) but not as a full 3-step QPB narrative; shell/adapter *step* dispatch and the monitor TOKENS column share asserted code paths but aren't separately asserted.

**VERDICT: SHIP**
