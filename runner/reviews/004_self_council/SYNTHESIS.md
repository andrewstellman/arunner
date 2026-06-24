# Instruction 004 — 3-panel self-Council synthesis

**Verdict: UNANIMOUS SHIP** (commit `55ffff5` on `fr-61-65-impl`, base `e6aa7d3`).

Three panels reviewed the atomic plan-format collapse against their charters.
The design was sound on every axis from round 1; the iteration was driven by
(a) a tooling accident and (b) one real schema↔engine agreement finding.

## Panels & charters
- **A — schema/format correctness:** mode oneOf complete + mutually exclusive; `additionalProperties:false` over-rejects nothing; `--check` ⟷ schema field-for-field; gate `outcomes` schema'd; per-mode `command` contract documented.
- **B — capability-preservation + atomicity + all-modes E2E + cross-repo.**
- **C — test sufficiency + honesty.**

## Round 1 (working tree, UNCOMMITTED) — all FIX-REQUIRED, but for ONE reason
Panel C, following its charter's "restore your mutation with `git checkout`"
instruction, ran `git checkout arunner/engine/tick.py` — which, because the
engine was **uncommitted**, reverted it to the `e6aa7d3` baseline and corrupted
the shared worktree mid-review. All three panels then (correctly) observed a
broken half-state (new-format everything + old-format engine) and returned
FIX-REQUIRED. **Their substantive design findings were positive:** capability
mapping complete (B), atomicity seam correct (B), all-modes E2E coverage present
(B), cross-repo flagged (B), pins bite + docs honest + gate-outcomes-schema-only
honest (C). Panel A additionally noted a real divergence (below).

**Resolution:** the engine survived in `/tmp/tick_backup.py` (a pre-mutation
backup); restored, suite re-confirmed 396 green, and **committed immediately**
(749bf47) so the tree could no longer be reverted by a `git checkout`. Lesson:
commit before a Council that may run `git checkout`.

## Round 2 (committed tree) — B SHIP, C SHIP, A FIX-REQUIRED (5 findings)
Panel A confirmed its round-1 cross-mode-mixing finding was addressed (each
`oneOf` branch now CLOSED: `additionalProperties:false` + per-mode property set;
empirical battery: schema rejects cross-mode keys in lockstep with the engine).
It then found 5 residual schema↔engine agreement gaps:
- **F1 (MEDIUM):** gate `outcomes`/`default` accepted any string; engine `_valid_outcome` enforces the closed set.
- **F2 (MEDIUM, real bug):** `skip-to-next:step-MM` is runtime-honored + documented but `_valid_outcome` rejected it at `--check`.
- **F3 (LOW):** engine didn't strict-key the `gate` object (schema did).
- **F4 (LOW):** engine didn't strict-key the plan root (schema did).
- **F5 (LOW):** schema `vars` was string-only; engine `_check_vars` allows string|number.

B and C returned **SHIP** with full evidence (B: complete old→new mapping table, zero half-rename stragglers, all-modes E2E run; C: mutation re-confirmed a pin bites, FRs+§9 added not freelanced, gate-outcomes-schema-only honesty confirmed against `git show e6aa7d3`, re-aimed tests retain teeth, 396 green).

**Resolution (committed in 55ffff5):**
- F2: `_valid_outcome` now accepts `skip-to-next:step-MM` (mirrors `_apply_gate_outcome`).
- F1: schema gate `outcomes`/`default` → a closed-set `gateOutcome` `$ref`.
- F3: `_check_gate` strict-keys against `_GATE_KEYS`.
- F4: `check_plan` strict-keys the plan root against `_PLAN_KEYS`.
- F5: schema `vars` value type widened to `["string","number"]`.
- New regression pins added (`test_check_plan.py::SchemaCheckAgreement`, 5 tests).

## Round 3 (focused confirmation) — A SHIP
Panel A re-ran a 33-case jsonschema-4.26 ⟷ `check_plan` battery: **zero
unsanctioned divergences**; all 5 findings fixed; no new divergence introduced;
`test_check_plan.py`+`test_gates.py` 48 green. The remaining 6 divergences are
sanctioned engine-only SEMANTIC checks the JSON schema cannot express (disk
repo-existence, shell heartbeat-route, the three reasoning-gate fences, vars
reserved-token/name, keepalive>grace, and the `defaults` pre-merge).

## Final state
- **A: SHIP · B: SHIP · C: SHIP** — unanimous.
- Suite: **401 passed ×3**, Python 3.14.6. Pins (per-mode-required, typo-rejection, unknown-mode, all-modes-E2E) mutation-verified to bite.
- Committed `55ffff5` on `fr-61-65-impl`, local only (not pushed).
</content>
