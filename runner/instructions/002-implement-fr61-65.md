# Instruction 002 — IMPLEMENT FR-61–65 (multi-step / prompt-from-file / gates / token reporting)

**Repo:** `~/Documents/arunner`, in a worktree `~/Documents/arunner-fr61-65-impl` on branch **`fr-61-65-impl`**, created off **`fr-61-65-spec`** (which carries the FR-61–65 spec + the three schema edits). Create: `git -C ~/Documents/arunner worktree add ~/Documents/arunner-fr61-65-impl -b fr-61-65-impl fr-61-65-spec`. Confirm branch. Do NOT work on `main` or `fr-61-65-spec` directly.

**One-line goal:** implement the FR-61–65 spec in the tick engine so arunner can run a multi-step, prompt-from-file, gated pipeline natively — the substrate for running QPB's phases through arunner instead of shelling out to `run_playbook`. Target arunner **0.2.0**.

## Read first (authoritative)
- `docs/REQUIREMENTS.md` — the FR-61–65 block (spec) + the §9 rows (currently PENDING). This is the contract to implement.
- `<RUNNER_ROOT>/FR61-65_DRAFT.md` — the spec + the 7 Council FIX-REQUIRED items already integrated into REQUIREMENTS.md; re-read so you implement the corrected behavior.
- `schemas/plan.schema.json`, `job_manifest.schema.json`, `result.schema.json` — already edited on `fr-61-65-spec`; implement to match.
- The tick engine + dispatch + heartbeat code these touch. NFR-3: the engine/ticker/CLI path stays **stdlib-only** — no runtime deps.

## Implement (each its own checkpoint commit)
1. **FR-61 prompt-from-file + `{var}` templating** — `worker_prompt_file` (resolved relative to the plan file's dir, snapshotted into the run-dir at `--init`); designated-key `{var}` substitution that runs BEFORE the engine's reserved placeholders and does NOT scan for stray braces (so QPB phase prompts' literal single-brace JSON survives — the Council FIX-2 case). Inline `worker_prompt` stays the default.
2. **FR-62 multi-step entries** — `steps: [...]`, sequential within one pool slot, per-step `run-NN/steps/step-MM/` disk state, `step_index`/`step_count`, dispatch-one-step-per-tick, resume-mid-sequence (completed steps reaped not re-run), monitor/TUI shows `step N of M`.
3. **FR-63 + FR-64 continuation gates + outcome vocabulary** — deterministic `kind:"shell"` gate (exit-code-only → outcome; the default, the only kind allowed in measurement runs), gate verdict persisted to `step-MM/gate.json` and read on resume; outcome set `continue` / `halt` (maps to an existing FR-55 verdict) / `skip-to-next` (synthesized `skipped` terminal) / `behavior-flag:<name>` (operator-declared name, exposed as a next-step `{var}`) / `internal_error` (fail-closed halt). **FR-63b reasoning gate** — implement it too, but fenced exactly per spec: separate judging context (same-context judge = `--check` error), structured logged verdict, off by default, rejected at `--check` in any `measurement: true` / FR-51-harness run.
4. **FR-65 token reporting** — read `data.usage = {input_tokens, output_tokens}` off heartbeats into top-level `result.schema.json` fields, additive roll-up per step/entry/run, surfaced in the status table + monitor + SUMMARY; degrade to `—`/partial honestly (never fabricate), never gate control flow.

## Tests + §9
- Implement the acceptance criteria each FR lists (mutation-verified where the spec says so), using the existing stdlib test harness — the FR-51 integration suite's independent checker must still pass. Keep new engine code stdlib-only.
- Flip each FR's `docs/REQUIREMENTS.md` §9 row to VERIFIED only when its tests prove it.
- Full suite green, run ≥3×; report counts + Python version.

## Council — mandatory 3-panel self-Council
`reviews/002_self_council/`, committed. Charters: **A — thesis/determinism** (disk-truth preserved; reasoning gate upholds FR-51 + fenced from measurement; tokens reporting-only). **B — schema/contract correctness** (implementation matches the edited schemas; resume + gate persistence on disk). **C — test sufficiency** (acceptance pins bite; mutation-verified; FR-51 checker green). Iterate to unanimous SHIP.

## Commit / scope
Checkpoint-commit per FR on `fr-61-65-impl`, local only. **Do NOT push, do NOT merge.** This is the implementation; a follow-up instruction will build the QPB-native plan (phases as steps, prompts from `phase_prompts/`, gates = `validate_phase_artifacts`) and run the recall benchmark through it.

## Output — `outputs/002-implement-fr61-65.md`
Per-FR implementation summary + checkpoint SHAs, the §9 rows flipped to VERIFIED, suite counts ≥3× + Python version, the 3-panel Council synthesis, and `git -C ~/Documents/arunner-fr61-65-impl log --oneline -8`. Note what remains: the QPB-native plan + the recall run.
