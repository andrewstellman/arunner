# Instruction 002 self-council synthesis — FR-61..65 implementation (multi-step / gates / prompt-from-file / token reporting), arunner 0.2.0

*Mandatory 3-panel self-Council. Three fresh-context, role-locked, adversarial reviewers verifying the IMPLEMENTATION on disk — tracing determinism/disk-truth and the FR-51/measurement fences, checking code-vs-schema-vs-spec, and performing live mutation probes against the test suite. Date: 2026-06-19. Implementation across 5 checkpoint commits (1557c6b FR-61, ff30411 FR-62, 3748e59 FR-63/64, 43f8bb9 FR-65, d1982b3 §9 flips) on branch `fr-61-65-impl`.*

| Panelist | Charter | Verdict |
|----------|---------|---------|
| `panelist_A_thesis_determinism.md` | disk-truth/NFR-6; reasoning gate upholds FR-51 + fenced from measurement; tokens reporting-only; shell gate exit-code-only; single-prompt path unaffected | **SHIP** |
| `panelist_B_schema_contract.md` | implementation matches the edited schemas; resume + gate persistence on disk; closed sets; no regression; pool/slot accounting | **SHIP** |
| `panelist_C_test_sufficiency.md` | acceptance pins covered; mutation-pins bite (live probes); FR-51 checker green; full suite deterministic | **SHIP** |

## Outcome: unanimous SHIP

### Panelist A — thesis/determinism (SHIP)
Gate verdicts persist to `step-MM/gate.json` and are read-on-resume, never recomputed (repro confirmed argv is skipped on resume); reaped steps never re-run. The reasoning gate is fully fenced (`--check` rejects without opt-in / in measurement / same-context / no distinct judge — all four reproduced), judged in a distinct sub-run, fail-closed on malformed/absent verdict. Tokens read exactly `data.usage`, never drive `{done,stop}`, degrade to `-` (no fabricated 0). The shell gate is exit-code-only (`stdout=DEVNULL`; an argv printing "FAILED" but exiting 0 → `continue`). Single-prompt path untouched.

### Panelist B — schema/contract (SHIP)
`--check` enforces the plan.schema.json `oneOf`; per-step manifests match the widened `dispatch_mode` enum + carry `step_index`/`step_count`; result token fields are top-level (not under `claimed`); the closed gate-kind/outcome sets are correct and `halt` maps to an EXISTING FR-55 terminal (no new terminal). heartbeat.schema.json byte-equality pin intact. `_holds_slot` gives a multi-step run exactly one slot across the sequence. One non-blocking doc-drift nit: plan.schema.json's `gate` object under-documents `outcomes`/`default`/`judge_*`/`same_context` (no validation conflict — the NFR-3 `--check` enforcer is correct).

### Panelist C — test sufficiency (SHIP)
Every acceptance pin for FR-61..65 has a behavioral assertion. Seven distinct mutations bit across all five FRs (additive-sum, out-of-set→internal_error, behavior-flag, no-usage-never-0/0, literal-brace, pool1-waits, plus the two added this round). Full suite 378 passed ×3, deterministic; the FR-51 independent checker stays green.

## Resolution of C's finding (test-evidence accuracy)
Panelist C accurately found that two original docstring mutation-claims named defense-in-depth guards (`_reap_step` `rp.exists()`; `_evaluate_gate` `gp.exists()`) that the *original* tests did not exercise — the correctness properties were genuinely proven via the `step_index`-advance mechanism, but the named guards were unbitten in those scenarios. **Resolved before declaring done:** added `test_step_reap_is_idempotent` and `test_gate_read_on_resume_after_crash_does_not_rerun_argv` (the crash-window that makes each guard load-bearing); both mutations were then verified to BITE (PASS→drop guard→FAIL→revert), and the two docstrings corrected to name the mutation that actually bites. This is a test-evidence accuracy improvement; no engine code changed.

## Disposition
No FIX-REQUIRED against the implementation. Five §9 rows flipped to VERIFIED. Full suite green 378 ×3 (Python 3.14.5). The non-blocking notes (plan.schema gate-object annotation; a `measurement`-run runtime re-fence as defense-in-depth; a full 3-step QPB Phase-3-skip narrative test; shell/adapter-step coverage) are recorded for follow-up, not gating. Implementation ships as the arunner 0.2.0 FR-61..65 substrate; the QPB-native plan + recall benchmark are the next instruction.
