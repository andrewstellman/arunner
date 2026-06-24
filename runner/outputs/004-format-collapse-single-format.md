# Output for 004-format-collapse-single-format.md
**Status:** completed

Atomic clean-sheet collapse of arunner's two-dialect plan format into ONE
mode-discriminated `jobs` format, on `fr-61-65-impl` (before it merges).
One commit (`55ffff5`), local only — **not pushed**. Suite **401 passed ×3**,
Python 3.14.6. 3-panel self-Council: **unanimous SHIP**.

## Before / after schema (the one format)
**Before (fr-61-65-impl @ e6aa7d3):** two dialects — `entries:` canonical
(`task_id`/`target_repo`/`dispatch_mode`/`worker_prompt`/`worker_cmd`/`adapter`/
`steps`) + `jobs:` shorthand (`id`/`repo`/`agent`/`adapter`/`prompt`), with
synonyms across them; `dispatch_mode∈{subagent,shell}` + `adapter∈{wrap,tail}`
as two separate discriminators; placeholders required in the prompt; no strict
keys; `schema_version "1"`.

**After:** a single `jobs` list. Each job: `id`, `repo`, `mode`, + the per-mode
field. `mode` is the one discriminator:

| `mode` | required | replaces |
|---|---|---|
| `agent` | one of `prompt`/`prompt_file` | `dispatch_mode:subagent` + `worker_prompt(_file)` |
| `command` | `command` | `adapter:"wrap"` + `command` (engine synthesizes the heartbeat; doneness = exit code) |
| `log` | `log_path` | `adapter:"tail"` (+ optional `command`/`success_regex`/`failure_regex`/`sentinel_file`/`pid`) |
| `pipeline` | `steps` | `steps` (each step its own `mode` + optional `gate`) |
| `shell` | `command` | `dispatch_mode:"shell"` + `worker_cmd` (raw argv; operator wires `{HEARTBEAT_PATH}`) |

`additionalProperties:false` + `description`/`_comment` at plan/job/step; optional
plan `defaults` merged under each job; gate `outcomes` folded into the schema;
`schema_version "2"`. The per-mode `command` contract is stated in the schema
field descriptions + TOOLKIT.md.

## Capability-mapping table — re-verified against the FINAL schema (nothing lost)
| old field | new home | verified |
|---|---|---|
| `entries` | `jobs` | ✓ |
| `task_id` | `id` (plan) / `task_id` (runtime record) | ✓ |
| `target_repo` | `repo` (plan) / `target_repo` (runtime) | ✓ |
| `dispatch_mode`+`adapter` | `mode` | ✓ |
| `worker_prompt`/`worker_prompt_file` | `prompt`/`prompt_file` (agent) | ✓ |
| `worker_cmd` | `command` (shell) / synthesized (command·log) | ✓ |
| `command`/`log_path`/`success_regex`/`failure_regex`/`sentinel_file`/`pid` | command/log modes | ✓ |
| `steps` | `pipeline` mode | ✓ |
| `auth_check` | command/shell (optional) | ✓ |
| `heartbeat_path` | agent/command/log/shell (optional) | ✓ |
| `vars` (plan+job+step) | preserved, 3-level merge intact | ✓ |
| `gate{kind,argv,skip_to,outcomes,default,judge_prompt[_file],same_context}` | pipeline step; `outcomes` now schema'd | ✓ |
| `measurement`/`allow_reasoning_gates` | plan-level fences | ✓ |
| `adapter_activity_patterns`/`keepalive_seconds`/per-job grace/stall | command/log | ✓ |
Executable proof: `tests/test_check_plan.py::CapabilityMappingCoverage`.

## Scope decision (the one architectural reading, defensible from the instruction)
The rename covers the **plan-authoring surface** (the keys the operator writes;
the engine reads them natively — no translation shim). The **runtime-record
vocabulary is preserved**: `manifest.json` / `results/*.json` /
`harness_status.json` runs records / the `dispatch_list` envelope / heartbeat
keep `task_id`/`target_repo`/`dispatch_mode`, and the `{TASK_ID}`/`{TARGET_REPO}`
placeholder TOKENS stay (settled decision 3). Grounded in: (1) settled decision 3
keeping the tokens; (2) the concrete-changes list excluding the runtime schemas;
(3) the instruction's own "steps reuse job_manifest.schema.json with dispatch_mode
widened." The plan→runtime mapping happens at the single `_scaffold_run`/
`_scaffold_step` boundary — the natural seam, NOT the two-DIALECT problem the
redesign kills.

## Files created / changed (86 files: +2321 / −1789)
| Path | Note |
|---|---|
| `schemas/plan.schema.json` (+ plugins mirror) | rewritten: mode oneOf with CLOSED per-mode branches (additionalProperties:false + per-mode property set), gate `outcomes`/`default` → closed-set `gateOutcome` $ref, strict keys + annotation, schema_version "2" |
| `arunner/engine/tick.py` | engine reads friendly `jobs`/`id`/`repo`/`mode`; `check_plan` rewritten (per-mode required + strict keys at plan/job/step/gate + gate outcomes); `_dispatch_mode_of`/`_adapter_worker_cmd` rekeyed on `mode`; auto-injected placeholder preamble (idempotent); `_valid_outcome` accepts `skip-to-next:step-MM`; runtime-vocab seam preserved |
| `arunner/engine/jobs.py` | collapsed to fill `defaults` + inject agent preamble (idempotent) |
| `arunner/cli.py` | preview (mode render) / add / msg + FR-60 message channel → new vocab |
| `tests/integration/runner.py` | held-worker detection on `command`; pipeline-aware settle (watches the current step's heartbeat) |
| `examples/*.json` (8, renamed from `*.jobs.json`) | rewritten to the one format |
| `tests/integration/scenarios/*` (20 converted + `pipeline_gate_completes` NEW) | command (engine-synth wrap) / log (engine-synth tail) / shell / pipeline+gate-outcomes E2E |
| `tests/*.py` (~30) + `tests/acceptance/plans/*` | embedded plans + field-name assertions updated; new pins added |
| `references/examples/*`, plugins reference plans | converted |
| `TOOLKIT.md` | format sections rewritten to the one format + per-mode `command` contract |
| `docs/REQUIREMENTS.md` | FR-66..69 + §9 rows added; FR-40/41 + dispatch_mode enum noted superseded; FR-70 stub + QPB follow-up filed |

## Commits made
`55ffff5` — *FR-66..69: collapse the plan format to one mode-discriminated `jobs` form* — on `fr-61-65-impl`, local only (not pushed/merged). (One amended commit; an intermediate `749bf47` was amended after the Council-driven schema/engine alignment.)

## Acceptance criteria — pass/fail per item
- One `jobs` list + one `mode` enum, per-mode required, `--check` enforces it — **PASS** (`test_check_plan.py`, schema oneOf).
- Folds FR-40/41 `adapter` + `dispatch_mode` enum into `mode`; supersession noted in §9 — **PASS**.
- Strict keys + `description`/`_comment` at plan/job/step — **PASS** (engine + schema, mutation-verified).
- Auto-injected preamble for `agent`/`pipeline` (format-only) — **PASS** (idempotent; pinned).
- Capability-preservation (every prior field maps) — **PASS** (table above + executable fixture).
- FR stub (opt-out heartbeat) filed, NOT implemented — **PASS** (FR-70 PLANNED).
- `schema_version "2"` — **PASS**.
- All-modes END-TO-END dispatch coverage — **PASS** (command/log/shell/pipeline integration scenarios; agent unit-pinned; mutation-verified to bite).
- QPB cross-repo break flagged NON-EXHAUSTIVE — **PASS** (FR-70 note + instruction).

## Council (required) — 3-panel self-Council: UNANIMOUS SHIP
`reviews/004_self_council/` (DESIGN.md = locked mapping/scope; SYNTHESIS.md = verdicts).
- **A (schema/format):** SHIP (round 3) — after fixing 5 round-2 schema↔engine gaps (gate-outcome closed set, parametric `skip-to-next:step-MM` at `--check`, gate strict-keys, plan-root strict-keys, vars-number); 33-case jsonschema↔`check_plan` battery = 0 unsanctioned divergences.
- **B (capability/atomicity/E2E/cross-repo):** SHIP — complete old→new mapping (no orphan), zero half-rename stragglers, all-modes E2E run green, QPB flagged.
- **C (test sufficiency/honesty):** SHIP — pins bite (mutation re-confirmed), FRs+§9 added not freelanced, gate-outcomes-schema-only honesty confirmed vs `git show e6aa7d3`, re-aimed tests retain teeth.
- **Process note:** round 1 was invalidated when a panelist's `git checkout` reverted the then-UNCOMMITTED engine; recovered from a backup, then committed before re-Council. Lesson recorded in SYNTHESIS.md.

## Tests
Baseline 379 (instr 003) → **401 passed**, run **×3** identical, `python3 -m pytest tests/ -q`, Python 3.14.6. stdlib-only engine preserved (NFR-3; `test_check_plan.py::test_stdlib_only_no_jsonschema` green — jsonschema used only in the Council battery, never imported by the engine). Mutation-verified pins: typo-rejection (strict keys), per-mode-required (command), unknown-mode, all-modes-E2E (command-mode mis-read → scenario can't complete) — each demonstrably FAILS when its check is removed; `__pycache__` purged before each re-verify.

## §9 rows flipped
Added (VERIFIED): FR-66 (one mode-discriminated format), FR-67 (strict keys + annotation), FR-68 (auto-injected preamble), FR-69 (capability-preservation). FR-70 (opt-out heartbeat contract + QPB follow-up) added as **PLANNED**. FR-40/41 row annotated **SUPERSEDED at the plan surface** (folded into `command`/`log` modes).

## Notable observations
- **The engine's internal wrap/tail synthesis + subagent/shell dispatch are unchanged** — only the discriminator the plan declares changed. This bounded the engine rewrite to plan-reading + `check_plan`.
- **shell mode has no `prompt`** (per the instruction's capability table — `worker_prompt`→`prompt` lives under `agent` only); a shell job carries the heartbeat route in its raw `command`. `{PROMPT_FILE}` stays reserved but resolves to an empty file for shell.
- **`defaults` is an engine-time pre-merge**; a `defaults`-using plan passes the engine `--check` (which merges first) but not a bare jsonschema validate — documented in the schema's `defaults` description.
- Found + fixed a latent test bug in `tests/test_cli.py` (`"agent":"subagent"` was never a valid key) during migration.

## Next action expected from orchestrator
Operator review + land `fr-61-65-impl` (with this collapse) per the usual FR-branch flow. **Required follow-ups (filed, NOT done here):**
1. **QPB cross-repo break** — a QPB-repo task that MUST begin with its own COMPLETE sweep for arunner-plan-key usage (`jobs`/`entries`/`mode`/`id`/`repo`/`prompt`/`command`/`task_id`/`target_repo`/`dispatch_mode`/`worker_prompt`/`worker_cmd`/`adapter`/`log_path`) before editing — the instruction's hit list is partial/non-exhaustive.
2. **FR-70** — the fully opt-out heartbeat CONTRACT (`heartbeat: auto`) reaching the dispatch/worker handshake (this instruction shipped only the format-only preamble auto-injection).
</content>
