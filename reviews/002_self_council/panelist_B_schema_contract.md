# Panelist B — Schema / Contract correctness (FR-61..65 implementation, instr 002)

**Charter:** the implementation matches the edited schemas; resume + gate persistence on disk; closed sets; no regression/drift; pool/slot accounting. (arunner schemas are not jsonschema-enforced — NFR-3 — so the hand-rolled `--check` in tick.py is the runtime enforcer; the review checks code-vs-schema-vs-spec.)

**Verified on disk (378/378 tests pass; all 3 schema JSONs well-formed; heartbeat.schema.json byte-untouched since FR-60, confirmed via git diff):**

1. **oneOf prompt-source.** `_check_entry` enforces exactly-one-of `{worker_prompt, worker_prompt_file, steps, adapter}` — matches plan.schema.json. Per-step source enforced in `_check_steps`.
2. **Per-step manifest.** `_scaffold_step` writes `dispatch_mode ∈ {subagent,shell}` (synthesized `shell` for adapter/worker_cmd steps) plus `step_index`+`step_count` — matches job_manifest.schema.json (widened enum + new optional props).
3. **Top-level tokens.** `_usage_of` returns top-level `input_tokens`/`output_tokens`, merged via `record.update(usage)` in `_move_to_results`, `_reap_step`, `_write_entry_result` — siblings of `summary`, NOT under `claimed`. Matches result.schema.json.
4. **Resume/gate persistence.** On-disk layout confirmed: `steps/step-MM/{heartbeat.ndjson,manifest.json,result.json,gate.json,prompt.snapshot.md}`; judge at `step-MM/gate/`. `step_index`+`step_count` in both the run record (harness_status.json) and the per-step manifest. gate.json records `outcome` verbatim + `kind`; reasoning gates add `judge` identity. Read-on-resume, never recomputed.
5. **Closed sets.** `_GATE_KINDS={shell,reasoning}`; outcomes `{continue,halt,skip-to-next,internal_error}` + parametric `behavior-flag:<name>`. `halt`→`failed`, FAILED/ABANDONED→`failed`, launch→`auth_or_launch_failed` — all EXISTING FR-55 terminals, no new ones. Out-of-set → `internal_error`→`failed`.
6. **Slot accounting.** `_holds_slot` uses `started` + non-terminal so a multi-step run holds exactly one slot across the between-steps `queued` window; `done`/counts recompute over `_TERMINAL_STATES`.

**Observation (non-blocking, doc-drift nit):** plan.schema.json's `gate` object documents `kind`/`argv`/`skip_to`, but `_check_gate` also reads/enforces `outcomes`, `default`, `judge_prompt`, `judge_prompt_file`, `same_context`. No `additionalProperties:false`, so these are permitted — no validation conflict, the code (the NFR-3 enforcer) is correct; the schema merely under-documents the contract. Recommend a follow-up schema annotation.

No contract mismatch between code, schema, and spec found.

**VERDICT: SHIP**
