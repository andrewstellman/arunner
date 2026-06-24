# Instruction 004 — collapse the plan/jobs format to ONE mode-discriminated format

## What this is
A clean-sheet redesign that collapses arunner's two-dialect plan format (`entries:` canonical + `jobs:` shorthand) into ONE format: a single `jobs` list with friendly keys and a single `mode` discriminator. Per the SETTLED DIRECTION in `docs/format_ux_review_2026-06-20.md` (lines 7-18): **no user base, nothing to migrate, no need to run old plans -> backward-compat is NOT a constraint.** This is a breaking redesign, done as ONE atomic change. The worker implements it red->green, runs the mandatory 3-panel self-Council, and reports per this instruction. The worker does NOT push (operator-only).

## Branch / base (verified)
- Target branch: **`fr-61-65-impl`** (confirmed on `refs/heads/fr-61-65-impl` @ `e6aa7d3`). The redesign replaces this branch's schema BEFORE it merges - not a separate change on `main`.
- Base schema replaced: `schemas/plan.schema.json` (182 lines, enumerated below).

## Grounding (verified against live artifacts; cite, don't assert)
Every field the current `fr-61-65-impl` entry/step can carry was enumerated and mapped to a new mode. **No field is orphaned** - the collapse reorganizes, it does not drop capability. Two verified facts the worker should not re-derive:
- **Gate `outcomes` map is a schema-only gap.** `_eval_shell_gate` reads `gate["outcomes"]` (`arunner/engine/tick.py:1774-1776`) AND `check_plan` already validates it (`tick.py:2780-2788`), but the JSON schema gate object (`plan.schema.json:109-130`) has only `kind`/`argv`/`skip_to`. So FOLD `outcomes` into the schema; do NOT "add" it to the engine (it is already read + validated).
- **Blast radius of the rename (honest sizing).** Not a small schema edit. `tick.py` is **3,096 lines** and references the old field names pervasively: `task_id` x42, `worker_prompt` x34, `dispatch_mode` x27, `worker_cmd` x20, `steps` x20, `target_repo` x17, `entries` x16, `adapter` x7, `command` x6. Plus `jobs.py` (expander, 129 lines), **~39 test files**, and **~20 integration scenario fixtures** (`tests/integration/scenarios/*/scenario.json`) embed plans. All rewritten ATOMICALLY (a partial rename leaves the engine unable to read its own plans).

### Capability-preservation map (old `fr-61-65-impl` field -> new home). The collapse must lose nothing.
**Plan level (stays top-level; only `entries`->`jobs` renames):**

| old | new | note |
|---|---|---|
| `entries` | **`jobs`** | the one list |
| `tick_interval_minutes`,`pool_size`,`stall_threshold_minutes`,`launch_grace_minutes`,`idle_tick_multiplier` | same | unchanged plan knobs |
| `vars` (plan) | `vars` | unchanged |
| `allow_reasoning_gates`,`measurement` | same | FR-63 |
| `schema_version` | `schema_version` | bump/redefine - see below |
| - | **`defaults`** (NEW, optional) | merged into each job |
| - | **`description`/`_comment`** (NEW, optional) | sanctioned annotation |

**Job level (was entry level):**

| old field | new field | new mode home |
|---|---|---|
| `task_id` | **`id`** | all modes (required) |
| `target_repo` | **`repo`** | all modes (required) |
| `dispatch_mode` + `adapter` | **`mode`** | the discriminator (required) |
| `worker_prompt` | **`prompt`** | `agent` |
| `worker_prompt_file` | **`prompt_file`** | `agent` |
| `steps` | `steps` | `pipeline` |
| `adapter:"wrap"` + `command` | `command` | **`command`** mode |
| `adapter:"tail"` + `log_path` | `log_path` | **`log`** mode (required) |
| `success_regex`,`failure_regex`,`sentinel_file`,`pid` | same | `log` (optional overlays) |
| `command` (tail-optional) | `command` | `log` (optional) |
| `worker_cmd` | **`command`** | **`shell`** mode |
| `auth_check` | `auth_check` | `command`/`shell` (optional) |
| `heartbeat_path` | `heartbeat_path` | common optional (command/log/shell) - FR-20 |
| `vars` (entry) | `vars` | common optional |

**Step level (inside `pipeline`; mirrors a job - gains its own `mode`):** `label`->same; `worker_prompt`->`prompt`; `worker_prompt_file`->`prompt_file`; `target_repo`->`repo` (per-step override); `worker_cmd`->`command`; `adapter`->per-step `mode`; `vars`->same; `gate{kind,argv,skip_to}`->`gate{kind,argv,skip_to,`**`outcomes`**`}` (fold the engine-read map into the schema).

## The settled design (the one format)
A single top-level **`jobs`** list. Friendly keys only: `id`, `repo`, `mode`, plus the per-mode field. `additionalProperties:false` + an optional `description`/`_comment` at plan/job/step level. A single `mode` discriminator drives a schema `oneOf`; each mode requires exactly its field, and `check_plan` (tick.py) enforces the same so malformed jobs fail at `--check`, not at dispatch:

| `mode` | required | optional | replaces |
|---|---|---|---|
| `agent` | one of `prompt`/`prompt_file` | `vars`,`heartbeat_path`,`description` | `dispatch_mode:subagent`+`worker_prompt(_file)` |
| `command` | `command` | `auth_check`,`heartbeat_path`,`vars`,`description` | `adapter:"wrap"`+`command` |
| `log` | `log_path` | `command`,`success_regex`,`failure_regex`,`sentinel_file`,`pid`,`heartbeat_path`,`vars`,`description` | `adapter:"tail"` |
| `pipeline` | `steps` | `vars`,`description` | `steps` (FR-62) |
| `shell` | `command` | `auth_check`,`heartbeat_path`,`vars`,`description` | `dispatch_mode:"shell"`+`worker_cmd` |

All modes also require `id`, `repo`, `mode`.

### Settled decisions (baked in - these are design constraints, not open questions)
1. **`shell` stays its own mode, reusing `command` as its argv key.** The docs (schema field descriptions + TOOLKIT.md) MUST state each mode's `command` contract explicitly:
   - **`command` mode:** the engine SYNTHESIZES the heartbeat plumbing around `command` (doneness = exit code). Operator wires nothing.
   - **`shell` mode:** the operator wires the heartbeat/placeholders themselves; `command` is the raw argv the engine Popens detached. This is the advanced escape hatch.
   - **`log` mode (optional `command`):** arunner LAUNCHES the process that writes `log_path` (vs. watching a log something else already writes).
   Keeping `shell` visibly distinct is deliberate: in `command` the engine guarantees the heartbeat; in `shell` the operator can forget it (the false-stall footgun) - a distinct mode keeps that risk legible.
2. **The working-directory field stays `repo`** (not `dir`/`path`).
3. **Placeholder auto-injection is format-only in THIS instruction:** the expander/engine injects the `{HEARTBEAT_PATH}/{TASK_ID}/{RUN_DIR}/{TARGET_REPO}/{HARNESS_BIN}` preamble for `agent`/`pipeline` prompts so authors never hand-type it. The placeholder TOKENS stay `{TASK_ID}` etc. (substitution tokens, not user keys - out of scope to rename). The deeper "heartbeating is a fully opt-out CONTRACT" change (reaching into the dispatch/worker handshake) is **a flagged follow-up FR, NOT in this instruction** - add the FR stub to REQUIREMENTS.md so it isn't lost, but do not implement it here.

## Scope reality (atomicity discipline)
"One format, one schema, end to end" necessarily means the **engine consumes the friendly shape directly** - there is no cheaper "keep `task_id` internally, rename only at the surface" path (that re-introduces the two-shapes/two-vocabularies problem this redesign exists to kill). So the ~180-reference rewrite in `tick.py` + the expander + tests + scenarios is the price of the goal. Do it as **ONE atomic change** (schema + engine + expander + all examples + all tests + all scenario fixtures together), red->green, mutation-verified, behind the 3-panel self-Council. Do not land it in partial slices.

## REQUIREMENTS (don't freelance - add the requirement)
Add to `docs/REQUIREMENTS.md` with section 9 ledger rows, council-reviewed:
- **FR - single mode-discriminated plan format.** One `jobs` list; one `mode` enum (`agent`/`command`/`log`/`pipeline`/`shell`); each mode's required field; `--check` enforces it. Folds/retires the FR-40/41 `adapter` selector and the `dispatch_mode` enum into `mode`; note the supersession in section 9.
- **FR - strict keys + sanctioned annotation.** `additionalProperties:false` + `description`/`_comment` at plan/job/step.
- **FR - auto-injected placeholder preamble** for `agent`/`pipeline` (format-only reach per settled decision 3).
- **FR - capability-preservation.** Every prior field maps to a mode (the table above is the acceptance artifact).
- **FR stub (follow-up, do NOT implement here)** - fully opt-out heartbeat contract (`heartbeat: auto`). Filed so it isn't lost.
- **schema_version treatment:** a clean redefinition is acceptable (nothing released). **Bump to `"2"`** as an unambiguous clean-break marker (the current schema description literally says "schema_version stays '1'" - that line goes); no migration note needed (no old plans exist).

## Concrete changes (lockstep - all in one atomic change)
1. `schemas/plan.schema.json` - rewrite to the one mode-discriminated schema (tables above): `jobs` list, `mode` `oneOf`, per-mode `required`, `additionalProperties:false` + `description`/`_comment` at plan/job/step, gate `outcomes` folded in, `schema_version:"2"`, per-mode `command` contract stated in field descriptions.
2. `arunner/engine/tick.py` - rewrite plan-reading to the friendly names (`id`/`repo`/`mode`/`prompt`/`prompt_file`/`command`/`steps`/...) across all ~180 references; make `check_plan` enforce the per-mode required + strict keys + the gate `outcomes` it already validates (one source of truth with the schema). Auto-inject the placeholder preamble for `agent`/`pipeline`.
3. `arunner/engine/jobs.py` - the expander collapses to **fill `defaults` + inject placeholders** (no dialect rename remains).
4. `examples/*.json` - rewrite ALL 8 to the new format (`agent_review`, `canonical_plan`, `mixed`, `shell_jobs`, `toolkit_walkthrough`, `uc10_four_exes`, `uc10_three_md_reviews`, `wrap_vs_tail`). The `.jobs.json`/canonical split disappears; rename files if the `.jobs.json` suffix no longer means anything.
5. `tests/` (~39 files) + `tests/integration/scenarios/*/scenario.json` (~20) - update every embedded plan + every field-name assertion in lockstep.
6. `TOOLKIT.md` format sections (`:66-150`) - the decision table (`:79-90`) is now the schema; rewrite prose to point at `mode`; state the per-mode `command` contract; document `description` and `defaults`; drop the two-dialect explanation.
7. Update arunner's own internal/runner plans to the new format in the same change.

## CROSS-REPO - QPB break (cannot fix from here; FLAG as required follow-up)
QPB emits/consumes arunner plans, so the rename breaks the QPB side. This cannot be fixed from the arunner repo (different repo; QPB source is hands-off). **Required follow-up task on the QPB repo.**

**IMPORTANT - this file list is NOT exhaustive.** It was located via a PARTIAL grep (the full-tree QPB grep timed out), so treat it as a starting point, not the complete set. **The QPB follow-up task MUST begin with its own complete sweep for arunner-plan-key usage across the whole QPB repo** (`jobs`/`entries`/`mode`/`id`/`repo`/`prompt`/`command`/`task_id`/`target_repo`/`dispatch_mode`/`worker_prompt`/`worker_cmd`/`adapter`/`log_path`) BEFORE editing - do not assume the list below is the full set.

Known (partial) hits:
- Plan JSONs to rewrite: `repos/integration-regression/plan.json` (uses `entries`/`task_id`/`target_repo`/`dispatch_mode`/`worker_prompt_file`/`steps`/`gate`), `testing/e2e_stub_plan.json`, `spike/v1.5.9_phase_1A/spike_plan.json`.
- Vendored harness code referencing plan keys: `bin/qpb_harness_tick.py`, `bin/harness_ticker.py`, `bin/harness_demo_worker.py` (vendored arunner engine pieces), and `bin/run_playbook.py` (the RETIRED path; may be deletable rather than updated).

This is out of THIS instruction's scope; flag it, do not treat it as done here.

## Tests (red->green, mutation-verified per AGENTS.md section 6)
Each pin reverted must demonstrably fail; record the bite in the docstring. Purge `__pycache__` before any post-restore re-verify.
- **Per-mode required:** `agent` without `prompt`/`prompt_file` FAILS `--check`; `command` without `command` FAILS; `log` without `log_path` FAILS; `pipeline` without `steps` FAILS; an **unknown `mode`** FAILS. (Mutation: drop a per-mode `oneOf` branch -> the malformed plan passes -> bite.)
- **Typo rejection:** a job with `promt`/`comand`/`reepo` FAILS `--check` via `additionalProperties:false`. (Mutation: remove `additionalProperties:false` -> typo passes -> bite.)
- **Annotation PASSES:** a plan/job/step carrying `description`/`_comment` validates.
- **Capability-mapping coverage:** a fixture per preserved field validates under its mode - `success_regex`+`failure_regex`+`sentinel_file`+`pid` (log), `heartbeat_path` (command), `auth_check` (shell), `vars` (plan+job+step merge), gate `outcomes` (pipeline step). Executable proof the collapse lost nothing.
- **Every rewritten `examples/*.json` validates**; the expander on each still `--check`-cleans; gate `outcomes` validates in-schema now.
- **ALL-MODES END-TO-END DISPATCH COVERAGE (the real risk of a ~180-ref atomic rename).** Schema/`--check` tests + a 2-mode smoke (agent + command) do NOT exercise the rewritten log/pipeline/shell plan-reading paths - a missed rename THERE could land with a fully-green schema suite and both smoke UCs. So after the rewrite, **confirm the integration scenarios collectively exercise EVERY mode's dispatch end-to-end (agent, command, log, pipeline, shell).** For any mode not already covered - most likely `shell`, `pipeline` with a gate that reads `outcomes`, and `log` with an optional `command` - **add a scenario fixture before landing.** Each such scenario must FAIL if the engine mis-reads that mode's fields.
- Full suite `python3 -m pytest tests/ -q` **>=3x**; report counts + Python version.

## Self-Council - mandatory 3-panel (reviews/004_self_council/, committed)
- **A - schema/format correctness:** the `mode` `oneOf` is complete and mutually exclusive; every preserved field maps to a mode (cross-check the capability table); `additionalProperties:false` over-rejects nothing legitimate (incl. `description`, `defaults`, all per-mode optionals); `--check` and the schema agree (one source of truth); gate `outcomes` correctly schema'd; each mode's `command` contract is stated in the docs.
- **B - capability-preservation + cross-repo + atomicity + all-modes E2E:** nothing from the `fr-61-65-impl` schema is dropped; all examples/tests/scenario fixtures/internal plans updated in ONE atomic change (no half-renamed engine); **every mode (agent/command/log/pipeline/shell) has >=1 end-to-end dispatch test that FAILS if the engine mis-reads that mode's fields** (this is the guard that makes the atomic rename safe); the QPB break is flagged as NON-EXHAUSTIVE with the required-complete-sweep note; lands on `fr-61-65-impl`.
- **C - test sufficiency + honesty:** per-mode / typo / mapping-coverage / all-modes-E2E pins bite (mutation-verified); the FRs + section 9 rows are added (not freelanced); the deeper opt-out-heartbeat change is recorded as a follow-up FR stub, NOT implemented; the gate-`outcomes` change is described as schema-only (engine already reads+validates); nothing claimed VERIFIED without a linked artifact.
Iterate to unanimous SHIP before reporting v1.

## Commit / scope / output
One atomic focused commit set on `fr-61-65-impl`; **worker does NOT push** (operator-only). Output -> `outputs/004-format-collapse.md`: the before/after schema, the capability-mapping table re-verified against the final schema, per-mode + typo + mapping-coverage + all-modes-E2E test evidence with mutation bites, all `examples/*` + scenario re-validation, the `schema_version:"2"` change, the new FR/section-9 rows (incl. the follow-up FR stub), the NON-EXHAUSTIVE QPB follow-up flag, the 3-panel synthesis, suite counts >=3x + Python version, `git log --oneline`.
