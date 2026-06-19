# Instruction 001 — land FR-61–65 spec (multi-step / gates / prompt-from-file / token reporting) into docs/REQUIREMENTS.md

**Repo:** `~/Documents/arunner`, in a **dedicated worktree** `~/Documents/arunner-fr61-65` on branch **`fr-61-65-spec`** (create it off `main`: `git -C ~/Documents/arunner worktree add ~/Documents/arunner-fr61-65 -b fr-61-65-spec`). Confirm the branch with `git -C ~/Documents/arunner-fr61-65 rev-parse --abbrev-ref HEAD`. Do NOT work on `main`.

**One-line goal:** integrate the Council-reviewed FR-61–65 draft into `docs/REQUIREMENTS.md` as arunner 0.2.0 spec — folding in all seven Council FIX-REQUIRED items — then self-Council the integration.

**This is a SPEC/docs change only** — no engine/CLI/test code implementation in this instruction (FR-61–65 get IMPLEMENTED in later instructions). Stdlib-only rule (NFR-3) still governs the eventual implementation; this instruction only writes requirements text.

## Read first
- `<RUNNER_ROOT>/FR61-65_DRAFT.md` — the Council-reviewed draft + the **seven FIX-REQUIRED items to integrate** (bottom section). The fixes are the spec — apply them into the FR text, don't just append them.
- `docs/REQUIREMENTS.md` — match the FR format/voice exactly; confirm the highest existing FR is **FR-60** (FR-61–65 are next, no collision); study FR-18 (single-`status` worker contract), FR-55 (continuation verdict closed set), FR-40/41/56 (engine-never-parses-text boundary + ReDoS bounds), FR-51 (never grades its own homework), NFR-3/6/11/12.
- `schemas/plan.schema.json`, `job_manifest.schema.json`, `heartbeat.schema.json`, `result.schema.json` — the contracts FR-61/62/65 touch.

## Work items
1. Write FR-61, FR-62, FR-63, FR-64, FR-65 into `docs/REQUIREMENTS.md` in the doc's style, **with the seven FIX-REQUIRED integrated**:
   - **#1** QPB Phase-3-skip is `behavior-flag` (worker-decided sentinel; Phase 4 always runs), NOT `skip-to-next`; keep `skip-to-next` generic with a non-QPB example.
   - **#2** `{var}` uses a designated replace-key pass that does NOT scan for stray braces (QPB phase3/phase5 have literal single-brace JSON); add the literal-brace-survives acceptance pin.
   - **#3** relax `plan.schema.json` `required` (drop unconditional `worker_prompt`; exactly-one-of via `oneOf`, mirroring `heartbeat.schema.json`); state it's a constraint relaxation. Update the schema file too.
   - **#4** gate `halt`/`internal_error` maps to an existing FR-55 verdict (`blocked:<id>`/`failed`), not a new terminal.
   - **#5** shell-gate outcome is exit-code-only (drop stdout-regex).
   - **#6** token result fields are top-level `result.schema.json` optional props; update the schema file.
   - **#7** widen per-step manifest `dispatch_mode` enum to include `shell`; update `job_manifest.schema.json`.
   - Fold the listed CONCERNs in as prose.
2. Add the §9 verification-matrix rows for FR-61–65 as **PENDING** (implementation lands later; do not mark VERIFIED — there are no tests yet).
3. Note at the top of the new block that these target arunner **0.2.0**.

## Council — mandatory 3-panel self-Council
`reviews/001_self_council/`, committed. Charters: **A — thesis fidelity** (determinism/disk-truth preserved; reasoning gate upholds FR-51; tokens reporting-only; no "engine parses text" reintroduced via the gate). **B — schema/contract** (numbering; `oneOf` relaxation correct; `data.usage` + top-level token fields fit the real schemas; per-step manifest enum widened). **C — internal consistency** (all 7 FIX-REQUIRED actually integrated; FR cross-refs resolve; §9 rows present as PENDING). Iterate to unanimous SHIP.

## Commit / scope
Commit on `fr-61-65-spec` (REQUIREMENTS.md + the three schema files + §9 rows + Council artifacts). **Do NOT push, do NOT merge to main** (operator lands FR branches after review). No version bump of pyproject/package.json (spec only; 0.2.0 bumps when the implementation ships).

## Output — `outputs/001-land-fr61-65-spec.md`
The integrated FR text summary, a checklist confirming each of the 7 fixes landed (with REQUIREMENTS.md line refs), the schema diffs, the 3-panel Council synthesis, and `git -C ~/Documents/arunner-fr61-65 log --oneline -5`. Note what remains: implementation instructions for each FR.

*(Housekeeping: there is a stray `runner/.write_test_*` file I created while probing mount writability and could not delete — please `git status`-ignore or `rm` it; it is not part of this work.)*
