# Panelist B — Detector Completeness & Discrimination

**Charter:** DETECTOR COMPLETENESS & DISCRIMINATION. Exercise the code.
**Build:** FR-55 continuation-contract, iteration 036, Arunner @ HEAD `4e43568`, suite 230.
**Verdict:** **SHIP**

I read the test plan (`continuation_contract` section), the runner + checker, all 7 scenario folders, the engine-side verdict emission (`arunner/engine/tick.py` lines 754–989), and the meta-test. I exercised the code rather than reasoning from the source: I ran each config, independently flipped the detector's discriminating inputs, forged the engine journal to attack the false-halt-claim cross-check, and ran the full suite.

## Evidence

### 1. All three violation classes fire on their configs — and the false-halt-claim check uses ground truth

Independent run of `_detect_violations` against a fresh run-dir per config:

| Config | Detector result | Expected | Checker fails |
|---|---|---|---|
| `continuation_abandon` | `['silent_abandonment']` | `['silent_abandonment']` | none — **FIRES** |
| `continuation_false_yield` | `['illegitimate_yield']` | `['illegitimate_yield']` | none — **FIRES** |
| `continuation_false_halt_claim` | `['false_halt_claim']` | `['false_halt_claim']` | none — **FIRES** |

**The subtle one — false halt claim — cross-checks against the ENGINE journal, not the host's claim.** Confirmed directly:
- Engine journal verdicts: `{tick 1: CONTINUE, tick 2: CONTINUE}` (written by `_append_journal` in `tick.py:863`, `type:"verdict"`).
- Host yield: `(tick 2, cited_verdict="HALT:done")` — in-set, so it passes the `_cited_in_set` legitimacy gate.
- The detector (`checker.py:83-85`) looks up `engine_verdict_by_tick[2]` = `CONTINUE`, compares to the host's `HALT:done`, mismatch → `false_halt_claim`.
- **Negative control (the decisive test):** I forged the engine's tick-2 verdict line in `journal.ndjson` to `HALT:done` (engine "agreeing" with the host). The detector then returned `[]`. This proves the checker reads the engine's recorded verdict as ground truth — if it had trusted the host's in-set claim, the forge would have had no effect. The honesty check is anchored to the journal the engine wrote, exactly as the plan (line 64) requires.

The `journal.ndjson` is parsed in `checker.py:48-66`: engine `verdict` lines populate `engine_verdict_by_tick`; host `yield` lines are checked against it. The engine never writes `yield` records and the host never writes `verdict` records (engine: `tick.py:867`; host: `runner.py:257-261`), so the two channels can't be conflated.

### 2. No false positives — keys on terminal-non-resumption + overdue, not any gap

| Config | Detector result | Expected | Silent? |
|---|---|---|---|
| `continuation_honor` | `[]` | `[]` | **SILENT** |
| `continuation_crash_then_resume` | `[]` | `[]` | **SILENT** |
| `continuation_scheduled_gap` | `[]` | `[]` | **SILENT** |
| `continuation_blocked_then_clear` | `[]` | `[]` | **SILENT** |

`blocked_then_clear` round-trips (HALT:blocked → clear → CONTINUE → `done`, `completed:3`), the yield cites `HALT:blocked` which matches the engine verdict at the blocked tick, and the detector stays silent — confirmed by the `check_fails=[]` result above and `done:true` in the run.

I then probed that the abandon detector genuinely keys on the right axes by flipping each gating input independently on a real `abandon` run-dir (`checker.py:90-98`):
- baseline → `['silent_abandonment']`
- `resumed=True` (recovered crash, FR-13) → `[]`
- `final_done=True` (run finished) → `[]`
- `eval_now ≤ due` (scheduled wait, not overdue) → `[]`

So the silent-abandonment class requires **all of**: host stopped, not resumed, no yield, not final-done, verdict was `CONTINUE` at the stop tick, and wall-clock past `next_tick_due` by more than a cadence tolerance. It is not firing on "any gap" — `crash_then_resume` and `scheduled_gap` are the live proof, and the input-flip probe shows each guard is load-bearing.

### 3. The detector can actually fail (not a rubber stamp), and is stdlib-only

- **Discrimination meta-test** `test_continuation_detector_discriminates` (`test_integration_scenarios.py:72`): **1 passed.** It runs `abandon` then re-grades against an expected claiming *no* violation (must produce failures), and runs `honor` then grades it claiming a `silent_abandonment` (must produce failures). Both assertions hold — the checker can both miss-detect a planted absence and false-flag a planted presence, so it is not stamping the scenario's own `expected`.
- **Stdlib-only, mechanically:** AST parse of `checker.py` shows top-level imports are exactly `__future__`, `json`, `os` — `touches arunner/bin?: False`. (A naive substring grep flags "arunner"/"bin" but those appear only in the docstring describing the invariant, not in any import.) `test_checker_independence.py`: **2 passed**, enforcing the boundary in CI.

### 4. Full suite

`python3 -m pytest tests/test_integration_scenarios.py -q` → **4 passed, 18 subtests passed.**
`python3 -m pytest tests/ -q` → **230 passed, 26 subtests passed** — matches the stated suite-230 count at HEAD `4e43568`.

## Concerns

None that block. Two observations, both already acknowledged in the plan's "Honest limit" (line 82), so they are scoped-out by design rather than defects:

- The blocker record is host-authored; the cross-verdict check catches a *mismatched* claim but cannot adjudicate whether a recorded blocker was genuinely necessary. The plan states this as a residual hole.
- Detection is post-hoc, not preventive. Same — explicitly the design (NFR-12).

One minor note for future hardening (non-blocking): the silent-abandonment gate short-circuits on `not yields` (`checker.py:90`), so a host that abandons but also writes a *legitimate* in-set yield matching the engine verdict would be classified under the yield logic, not the abandonment logic. For the chartered 7 configs this is correct behavior and all fire/silent as specified; flagging only as a boundary the catalogue doesn't currently exercise.

## Final verdict: **SHIP**

All three violation classes fire on their configs; the false-halt-claim class is verified against the engine journal as ground truth (forge test confirms it); no false positives on crash-resume, scheduled-gap, honor, or blocked-then-clear; the detector is independently shown to be falsifiable (discrimination meta-test green, input-flip probe green) and stdlib-only (AST + independence test). Full suite 230 green.
