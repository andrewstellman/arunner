# Output for 001-land-fr61-65-spec.md

**Status:** completed

## Files created / changed
*(all in worktree `~/Documents/arunner-fr61-65`, branch `fr-61-65-spec`)*

| Path | Lines | Note |
|------|-------|------|
| `docs/REQUIREMENTS.md` | +32/-4 | New `### Multi-step / gated-pipeline / token-reporting additions (arunner 0.2.0)` block (FR-61..65) after FR-60; 5 §9 PENDING rows; v1.4 status-line + footer notes |
| `schemas/plan.schema.json` | +69/-4 | FIX #3: entry `required` relaxed (dropped `worker_prompt`) + `oneOf` over {worker_prompt\|worker_prompt_file\|steps\|adapter}; new props `worker_prompt_file`/`vars`/`steps`(+nested `gate`); plan-level `vars`/`allow_reasoning_gates`/`measurement` |
| `schemas/result.schema.json` | +10 | FIX #6: top-level optional `input_tokens`/`output_tokens` (siblings of `summary`/`synthesized`, not under `claimed`) |
| `schemas/job_manifest.schema.json` | +12/-1 | FIX #7: `dispatch_mode` enum widened `["subagent"]`→`["subagent","shell"]`; optional `step_index`/`step_count` for per-step sub-runs |
| `reviews/001_self_council/panelist_A_thesis_fidelity.md` | 19 | Council panel A |
| `reviews/001_self_council/panelist_B_schema_contract.md` | 19 | Council panel B |
| `reviews/001_self_council/panelist_C_internal_consistency.md` | 23 | Council panel C |
| `reviews/001_self_council/synthesis.md` | 23 | Council synthesis — unanimous SHIP |

Housekeeping: removed the stray probe files `runner/.write_test_2` and `.__wtest` (operator-requested; not part of this work).

## Commits made
`aaecd2c` — *FR-61..65 spec: multi-step / gates / prompt-from-file / token reporting (instr 001)* — on branch `fr-61-65-spec`, **local only (not pushed, not merged)**. Staged: REQUIREMENTS.md + the three schema files + the four Council artifacts.

## Acceptance criteria — pass/fail per item
| Work item | Result |
|-----------|--------|
| FR-61..65 written in the doc's style after FR-60 | **PASS** |
| FIX #1 — Phase-3-skip = `behavior-flag` (worker-written sentinel, Phase 4 always runs); `skip-to-next` generic w/ non-QPB example; pin asserts sentinel-read | **PASS** (FR-64) |
| FIX #2 — designated replace-key pass, no stray-brace scan; literal-single-brace acceptance pin | **PASS** (FR-61) |
| FIX #3 — `plan.schema.json` `required` relaxed; exactly-one-of `oneOf`; called a constraint relaxation; schema updated | **PASS** |
| FIX #4 — gate `halt`/`internal_error` → existing FR-55 verdict (`failed`/`blocked:<id>`), no new terminal | **PASS** (FR-64) |
| FIX #5 — shell gate exit-code-only (stdout-regex dropped) | **PASS** (FR-63) |
| FIX #6 — token result fields top-level, not under `claimed`; schema updated | **PASS** |
| FIX #7 — per-step manifest `dispatch_mode` enum widened to include `shell`; schema updated | **PASS** |
| Concerns folded as prose (verdict-once+persisted; flag-name operator-declared; engine reads exactly `data.usage`; concrete QPB-precondition reference gate; run_playbook → TOKENS `—`) | **PASS** |
| §9 rows for FR-61..65 added as PENDING (not VERIFIED) | **PASS** (five rows) |
| 0.2.0 target noted at top of the new block | **PASS** |
| No pyproject/package.json version bump | **PASS** (none made) |

## Council (if required)
Mandatory 3-panel self-Council — **unanimous SHIP, round 1**. Artifacts: `reviews/001_self_council/` (panelists A/B/C + `synthesis.md`). Three fresh-context adversarial reviewers verified on disk: A (thesis fidelity — determinism/disk-truth, FR-51 reasoning-gate fence, tokens reporting-only, no engine-parses-text), B (schema/contract — numbering, `oneOf` correctness + no existing-plan breakage, top-level token fields, manifest enum, JSON well-formed, heartbeat byte-pin intact), C (internal consistency — all 7 FIX integrated + quoted, concerns folded, five PENDING §9 rows, all cross-refs resolve). No FIX-REQUIRED raised.

## Tests
Baseline (this branch off `main`, `cf67781`): **334 passed**, Python 3.14.5. Final after edits: **334 passed** (`python3 -m pytest -q`, 36.85s). Spec/schema-only change — no test count change, no regression. Targeted `test_schemas.py` + `test_check_plan.py` = 18 passed; all three edited JSON files parse clean. `heartbeat.schema.json` deliberately untouched (byte-identical cross-skill PIN preserved).

## §9 rows flipped
**None flipped to VERIFIED** — by design. Five rows ADDED as **PENDING** (FR-61, FR-62, FR-63, FR-64, FR-65), each tagged arunner 0.2.0, naming its schema delta and the deferred implementation/tests. Rows flip to VERIFIED only when the implementation instructions ship passing tests.

## Notable observations
- **Worktree-name vs FR-number collision (informational, not blocking):** pre-existing worktrees `~/Documents/arunner-fr61` (branch `fr-61-subagent-liveness`) and `~/Documents/arunner-fr62` (branch `fr-62-tui`) use the numbers 61/62 informally for unrelated WIP. The authoritative spec (`docs/REQUIREMENTS.md`) tops out at FR-60, so FR-61..65 are the correct next numbers and there is no collision in the requirements. Flagging in case the orchestrator wants to rename those branches.
- **FIX #3 also closed a latent pre-existing defect:** `plan.schema.json` previously listed `worker_prompt` in entry `required`, yet adapter entries legitimately omit it — so the old schema would have rejected every valid adapter plan under a strict validator. The `oneOf` relaxation fixes that inconsistency too.
- **Schemas are documentation, not runtime-enforced:** NFR-3 forbids a `jsonschema` dependency; the stdlib `--check` validator is the enforcer. These `.json` edits are contract docs — the implementation instructions must teach `--check` the new `oneOf`/fields.
- **Implementation deliverables for `--check` (for later instructions):** worker_prompt+worker_prompt_file mutual exclusion; vars-key/reserved-name collision + reserved-token-in-vars-value errors; prompt+steps mutual exclusion; same-context reasoning-judge rejection; reasoning-gate rejection in measurement/FR-51/FR-55 runs; `keepalive`-style screens are unaffected.

## Next action expected from orchestrator
Review the `fr-61-65-spec` branch and land it (operator merges FR branches; the worker does not push/merge). Then file the implementation instructions for FR-61..65 (each flips its §9 row to VERIFIED when its tests pass). Optionally rename the informally-numbered `fr-61-subagent-liveness` / `fr-62-tui` worktrees to avoid future number confusion.
