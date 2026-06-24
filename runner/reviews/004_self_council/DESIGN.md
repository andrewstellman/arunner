# Instruction 004 — locked design contract

The single source of truth for the format collapse. The engine rewrite, every
fixture/test update, and the 3-panel Council all reference THIS mapping.

## The one format (mode-discriminated `jobs` list)

```jsonc
{
  "schema_version": "2",
  "pool_size": 2,              // + the other plan knobs, unchanged
  "vars": { ... },            // plan-level, unchanged
  "allow_reasoning_gates": false, "measurement": false,  // FR-63, unchanged
  "defaults": { ... },        // NEW optional: shallow-merged under each job
  "description": "...",       // NEW optional annotation (also _comment)
  "jobs": [
    {"id": "...", "repo": "/abs", "mode": "agent",   "prompt": "..."},
    {"id": "...", "repo": "/abs", "mode": "command", "command": ["pytest","-q"]},
    {"id": "...", "repo": "/abs", "mode": "log",     "log_path": "/abs/build.log"},
    {"id": "...", "repo": "/abs", "mode": "pipeline","steps": [ ... ]},
    {"id": "...", "repo": "/abs", "mode": "shell",   "command": ["claude","--print", ...]}
  ]
}
```

All jobs require `id`, `repo`, `mode`. `additionalProperties:false` at
plan/job/step. `description`/`_comment` allowed at every level.

### per-mode required / optional
| mode | required | optional |
|---|---|---|
| `agent` | one of `prompt` / `prompt_file` | `vars`, `heartbeat_path`, `description`, `_comment` |
| `command` | `command` (argv) | `auth_check`, `heartbeat_path`, `vars`, `adapter_activity_patterns`, `keepalive_seconds`, `launch_grace_minutes`, `stall_threshold_minutes`, `description`, `_comment` |
| `log` | `log_path` | `command`, `success_regex`, `failure_regex`, `sentinel_file`, `pid`, `heartbeat_path`, `vars`, `adapter_activity_patterns`, `keepalive_seconds`, `launch_grace_minutes`, `stall_threshold_minutes`, `description`, `_comment` |
| `pipeline` | `steps` | `vars`, `description`, `_comment` |
| `shell` | `command` (raw argv) | `auth_check`, `heartbeat_path`, `vars`, `description`, `_comment` |

Step (inside `pipeline`) mirrors a job, minus `steps`/pipeline: requires `mode`
+ its per-mode field; optional `label`, `repo` (per-step override), `vars`,
`gate`, `description`/`_comment`. Step modes: `agent`/`command`/`log`/`shell`.
Gate object: `{kind, argv, skip_to, outcomes, default, judge_prompt[_file], same_context}`
(`outcomes` folded into the schema; engine already reads+validates it).

## old (fr-61-65-impl) -> new key mapping (PLAN-AUTHORING surface only)

| old plan key | new key |
|---|---|
| `entries` | `jobs` |
| entry `task_id` | `id` |
| entry/step `target_repo` | `repo` |
| `dispatch_mode:"subagent"` + `worker_prompt` | `mode:"agent"` + `prompt` |
| `worker_prompt_file` | `prompt_file` |
| `dispatch_mode:"shell"` + `adapter:"wrap"` + `command` | `mode:"command"` + `command` |
| `dispatch_mode:"shell"` + `adapter:"tail"` + `log_path` | `mode:"log"` + `log_path` |
| `dispatch_mode:"shell"` + `worker_cmd` (raw) | `mode:"shell"` + `command` |
| `steps` | `mode:"pipeline"` + `steps` |
| step `adapter`/`worker_cmd`/`dispatch_mode` | step `mode` |
| step `worker_prompt`/`worker_prompt_file`/`worker_cmd` | `prompt`/`prompt_file`/`command` |

`command`, `log_path`, `success_regex`, `failure_regex`, `sentinel_file`,
`pid`, `auth_check`, `heartbeat_path`, `vars`, `gate`, `label`,
`adapter_activity_patterns`, `keepalive_seconds`, the plan knobs, `gate` keys —
all KEEP their names.

## SCOPE BOUNDARY (the load-bearing decision)

The rename covers the **plan-authoring surface** — the keys an operator writes
and the engine reads natively from the plan/job/step. The engine consumes the
friendly shape directly (no expand-to-old-shape shim).

The **runtime-record vocabulary is preserved**: on-disk artifacts the engine
WRITES — `manifest.json`, `results/result-*.json`, `harness_status.json` runs
records, the `claimed/*.lock`, the heartbeat, and the **dispatch envelope**
(`dispatch_list` items) — keep `task_id` / `target_repo` / `dispatch_mode` /
`worker_prompt` / `worker_cmd`. Justification, all from the instruction itself:
- Settled decision 3 preserves the `{TASK_ID}`/`{TARGET_REPO}`/`{RUN_DIR}`/
  `{HEARTBEAT_PATH}` placeholder TOKENS verbatim — the runtime identity stays
  `task_id`.
- The concrete-changes list (instr §"Concrete changes") names plan.schema.json,
  tick.py plan-reading, jobs.py, examples, tests, scenarios, TOOLKIT,
  REQUIREMENTS — NOT job_manifest/heartbeat/result schemas.
- The instruction's own grounding says steps "reuse job_manifest.schema.json
  with dispatch_mode widened" — i.e. the manifest keeps `dispatch_mode`.

The mapping happens at the single plan-read boundary (job -> manifest/record/
dispatch envelope). That is the natural plan-vocab <-> runtime-vocab seam, NOT
the reintroduced two-DIALECT authoring problem the redesign kills (which was
`entries:`/`jobs:` + `id`/`task_id` synonyms across shorthand vs full form).

Consequence for fixtures: a scenario.json's `plan` block renames; its
`expected` runtime block (run_states/counts) is unchanged. A test that asserts
on `dispatch_list[i]["worker_prompt"]` / manifest `task_id` keeps that
assertion; only the PLAN it builds changes keys.

## Internal dispatch mapping (mode -> existing engine machinery)

The engine keeps its wrap/tail heartbeat-synthesis + subagent/shell dispatch;
`mode` selects it:
- `agent`   -> dispatch_mode subagent; prompt = job `prompt`/`prompt_file`; engine AUTO-INJECTS the placeholder preamble.
- `command` -> dispatch_mode shell; synthesize the `wrap` adapter worker_cmd around job `command`.
- `log`     -> dispatch_mode shell; synthesize the `tail` adapter worker_cmd around `log_path` (+ optional command/markers/pid).
- `shell`   -> dispatch_mode shell; worker_cmd = job `command` (raw; operator wires the heartbeat).
- `pipeline`-> steps; each step dispatches by its own `mode` (same table).

## Auto-injected placeholder preamble (settled decision 3)

For `agent` jobs and `agent` pipeline steps, the ENGINE prepends the
`HEARTBEAT_PATH={HEARTBEAT_PATH}\n…` preamble before substitution, so authors
write a bare prompt. `--check` no longer REQUIRES the placeholders be present in
an agent prompt (they are injected); it still rejects an unknown `{TYPO}`
placeholder token. `shell` mode does NOT auto-inject — the operator wires the
heartbeat route (the deliberate footgun-visible escape hatch); `--check` still
enforces the heartbeat route for shell. `command`/`log` need no prompt (engine
synthesizes the plumbing). The placeholder TOKENS stay `{TASK_ID}` etc.

## schema_version

Clean break to `"2"`. No migration note (no released plans).

## Out of scope (flag, do not implement)
- Fully opt-out heartbeat CONTRACT (`heartbeat: auto`) — FR stub only.
- QPB cross-repo break — required follow-up on the QPB repo; the QPB task must
  begin with its OWN complete sweep (the instruction's hit list is partial).
</content>
</invoke>
